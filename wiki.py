import warnings
from bs4 import BeautifulSoup, GuessedAtParserWarning

warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+",
    category=Warning,
)
warnings.filterwarnings(
    "ignore",
    category=GuessedAtParserWarning,
    module=r"wikipedia\.wikipedia",
)

import wikipedia # https://wikipedia.readthedocs.io/en/latest/code.html#api
import wikipedia.wikipedia as wikipedia_impl
import json
import sqlite3
import spacy
from sklearn.metrics.pairwise import cosine_similarity
from typing import Any, Dict, List, Optional, Tuple


def _patched_beautiful_soup(markup: str, *args: Any, **kwargs: Any) -> BeautifulSoup:
    if not args and "features" not in kwargs:
        kwargs["features"] = "html.parser"
    return BeautifulSoup(markup, *args, **kwargs)


wikipedia_impl.BeautifulSoup = _patched_beautiful_soup

MAX_PATH_LENGTH = 20
MAX_SEARCH_STEPS = 100
MAX_BRANCHES_PER_PAGE = 5

Page = Any
Embedding = Any
PageCache = Dict[str, Optional[Page]]
LinkCache = Dict[Tuple[str, bool], List[str]]
EmbeddingCache = Dict[Tuple[str, str], Optional[Embedding]]

# Load spacy model once at module level
nlp = spacy.load("en_core_web_sm")

# create the database if it doesn't exist
conn = sqlite3.connect("pages.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS pages (name TEXT, links TEXT)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_name ON pages(name)")
conn.commit()

def encode_text(text: str) -> Embedding:
    """Encode text using spacy's sentence vectors"""
    doc = nlp(text)
    return doc.vector.reshape(1, -1)


def _serialize_page_edges(page: Page) -> str:
    return json.dumps({
        "links": page.links,
        "categories": page.categories,
    })


def _get_cached_page_edges(page_name: str, cached_value: str, page_cache: PageCache) -> Dict[str, List[str]]:
    parsed_value = json.loads(cached_value)
    if isinstance(parsed_value, dict):
        return {
            "links": parsed_value.get("links", []),
            "categories": parsed_value.get("categories", []),
        }

    page = _get_page_cached(page_name, page_cache)
    if page is None:
        return {
            "links": parsed_value,
            "categories": [],
        }

    return {
        "links": page.links,
        "categories": page.categories,
    }

# TODO: Returns the Python page too often.
def get_page(page_name: str) -> Optional[Page]:
    """Get a specific Wikipedia page by name"""
    try:
        return wikipedia.page(page_name, auto_suggest=False, redirect=False)
    except:
        pass
    try:
        search_results = wikipedia.search(page_name)
        if not search_results:
            return None
        choice = search_results[0]
        page = wikipedia.page(choice, auto_suggest=False, redirect=False)
        return page
    except:
        return None

def get_page_links_with_cache(
    page_name: str,
    page_cache: Optional[PageCache] = None,
    link_cache: Optional[LinkCache] = None,
    ignore_categories: bool = False,
) -> List[str]:
    if page_cache is None:
        page_cache = {}
    if link_cache is None:
        link_cache = {}
    return _load_page_links(page_name, page_cache, link_cache, ignore_categories)

def _get_page_cached(page_name: str, page_cache: PageCache) -> Optional[Page]:
    if page_name not in page_cache:
        page_cache[page_name] = get_page(page_name)
    return page_cache[page_name]

def _load_page_links(page_name: str, page_cache: PageCache, link_cache: LinkCache, ignore_categories: bool) -> List[str]:
    cache_key = (page_name, ignore_categories)
    if cache_key in link_cache:
        return link_cache[cache_key]

    conn = sqlite3.connect("pages.db")
    cursor = conn.cursor()
    cached_page = cursor.execute("SELECT * FROM pages WHERE name = ?", (page_name,)).fetchone()

    if not cached_page:
        page = _get_page_cached(page_name, page_cache)
        if page is None:
            conn.close()
            link_cache[cache_key] = []
            return []
        cursor.execute("INSERT INTO pages (name, links) VALUES (?, ?)", (page_name, _serialize_page_edges(page)))
        conn.commit()
        cached_page = cursor.execute("SELECT * FROM pages WHERE name = ?", (page_name,)).fetchone()

    edge_data = _get_cached_page_edges(page_name, cached_page[1], page_cache)
    if not isinstance(json.loads(cached_page[1]), dict):
        cursor.execute("UPDATE pages SET links = ? WHERE name = ?", (_serialize_page_edges(_get_page_cached(page_name, page_cache)), page_name))
        conn.commit()

    conn.close()

    links = edge_data["links"]
    if not ignore_categories:
        links = links + edge_data["categories"]

    filtered = [link for link in links if is_regular_page(link)]
    if page_name in filtered:
        filtered.remove(page_name)
    link_cache[cache_key] = filtered
    return filtered

def is_regular_page(page_name: str) -> bool:
    normalized_name = page_name.lower()
    meta_patterns = [
        "disambiguation",
        "automatic",
        "article",
        "page",
        "identifier",
        "wikidata",
        "wikipedia",
        "short description",
        "template:",
        "help:",
        "user:",
    ]
    return not any(pattern in normalized_name for pattern in meta_patterns)

# TODO: Gotta speed this up. It's OK if we don't get the shortest path, but we should get *a* path.
# TODO: Add a timeout to the search. 10 seconds?
def _get_summary_embedding(page_name: str, page_cache: PageCache, embedding_cache: EmbeddingCache) -> Optional[Embedding]:
    cache_key = ("summary", page_name)
    if cache_key not in embedding_cache:
        page = _get_page_cached(page_name, page_cache)
        if page is None or not page.summary:
            embedding_cache[cache_key] = None
        else:
            embedding_cache[cache_key] = encode_text(page.summary)
    return embedding_cache[cache_key]

def _get_title_embedding(page_name: str, embedding_cache: EmbeddingCache) -> Embedding:
    cache_key = ("title", page_name)
    if cache_key not in embedding_cache:
        embedding_cache[cache_key] = encode_text(page_name)
    return embedding_cache[cache_key]

def _score_candidate(page_name: str, target_embedding: Optional[Embedding], page_cache: PageCache, embedding_cache: EmbeddingCache) -> float:
    candidate_embedding = _get_title_embedding(page_name, embedding_cache)
    if candidate_embedding is None or target_embedding is None:
        return float("-inf")
    return cosine_similarity(candidate_embedding, target_embedding)[0][0]

def _find_short_path(
    start_page_name: str,
    end_page_name: str,
    page_cache: PageCache,
    link_cache: LinkCache,
    embedding_cache: EmbeddingCache,
    ignore_categories: bool,
) -> Optional[List[str]]:
    """Find a valid path using a bounded greedy best-first search."""

    if start_page_name == end_page_name:
        return [start_page_name]

    target_embedding = _get_summary_embedding(end_page_name, page_cache, embedding_cache)
    if target_embedding is None:
        return None

    frontier: List[Tuple[float, List[str]]] = [(0.0, [start_page_name])]
    visited = {start_page_name}
    steps = 0

    while frontier and steps < MAX_SEARCH_STEPS:
        best_index = max(range(len(frontier)), key=lambda index: (frontier[index][0], frontier[index][1]))
        _, path = frontier.pop(best_index)
        current_page = path[-1]

        if len(path) >= MAX_PATH_LENGTH:
            steps += 1
            continue

        links = _load_page_links(current_page, page_cache, link_cache, ignore_categories)
        if end_page_name in links:
            return path + [end_page_name]

        scored_candidates: List[Tuple[float, List[str]]] = []
        for link in links:
            if link in visited or link in path:
                continue
            score = _score_candidate(link, target_embedding, page_cache, embedding_cache)
            scored_candidates.append((score, path + [link]))

        scored_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)

        for score, next_path in scored_candidates[:MAX_BRANCHES_PER_PAGE]:
            frontier.append((score, next_path))
            visited.add(next_path[-1])

        steps += 1

    return None


def find_short_path(
    start_page: Page,
    end_page: Page,
    page_cache: Optional[PageCache] = None,
    link_cache: Optional[LinkCache] = None,
    embedding_cache: Optional[EmbeddingCache] = None,
    ignore_categories: bool = False,
) -> Optional[List[str]]:
    if page_cache is None:
        page_cache = {}
    page_cache[start_page.title] = start_page
    page_cache[end_page.title] = end_page
    if link_cache is None:
        link_cache = {}
    if embedding_cache is None:
        embedding_cache = {}

    return _find_short_path(start_page.title, end_page.title, page_cache, link_cache, embedding_cache, ignore_categories)