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
import time
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
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_PERSISTENT_CACHE_ROWS = 1000
CACHE_CLEANUP_WRITE_INTERVAL = 25
MAX_LINK_CACHE_SIZE = 256
MAX_EMBEDDING_CACHE_SIZE = 512
CACHE_DB_PATH = "pages.db"

Page = Any
Embedding = Any
PageCache = Dict[str, Optional[Page]]
LinkCache = Dict[Tuple[str, bool], List[str]]
EmbeddingCache = Dict[Tuple[str, str], Optional[Embedding]]

_cache_writes_since_cleanup = 0

# Load spacy model once at module level
nlp = spacy.load("en_core_web_sm")

def encode_text(text: str) -> Embedding:
    """Encode text using spacy's sentence vectors"""
    doc = nlp(text)
    return doc.vector.reshape(1, -1)


def _current_timestamp() -> int:
    return int(time.time())


def _get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_cache_schema(conn)
    return conn


def _ensure_cache_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS pages (name TEXT, links TEXT)")

    columns = {row[1] for row in cursor.execute("PRAGMA table_info(pages)").fetchall()}
    if "updated_at" not in columns:
        cursor.execute("ALTER TABLE pages ADD COLUMN updated_at INTEGER")
    if "last_accessed_at" not in columns:
        cursor.execute("ALTER TABLE pages ADD COLUMN last_accessed_at INTEGER")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_name ON pages(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_last_accessed_at ON pages(last_accessed_at)")

    now = _current_timestamp()
    cursor.execute(
        """
        UPDATE pages
        SET updated_at = COALESCE(updated_at, ?),
            last_accessed_at = COALESCE(last_accessed_at, ?)
        WHERE updated_at IS NULL OR last_accessed_at IS NULL
        """,
        (now, now),
    )
    conn.commit()


def _fetch_cached_page_row(cursor: sqlite3.Cursor, page_name: str) -> Optional[sqlite3.Row]:
    return cursor.execute(
        """
        SELECT name, links, updated_at, last_accessed_at
        FROM pages
        WHERE name = ?
        ORDER BY rowid DESC
        LIMIT 1
        """,
        (page_name,),
    ).fetchone()


def _touch_cached_page(cursor: sqlite3.Cursor, page_name: str, now: int) -> None:
    cursor.execute(
        "UPDATE pages SET last_accessed_at = ? WHERE name = ?",
        (now, page_name),
    )


def _write_cached_page(cursor: sqlite3.Cursor, page_name: str, page: Page, now: int) -> None:
    serialized_edges = _serialize_page_edges(page)
    updated_rows = cursor.execute(
        """
        UPDATE pages
        SET links = ?, updated_at = ?, last_accessed_at = ?
        WHERE name = ?
        """,
        (serialized_edges, now, now, page_name),
    ).rowcount

    if updated_rows == 0:
        cursor.execute(
            """
            INSERT INTO pages (name, links, updated_at, last_accessed_at)
            VALUES (?, ?, ?, ?)
            """,
            (page_name, serialized_edges, now, now),
        )


def _record_cache_write() -> None:
    global _cache_writes_since_cleanup
    _cache_writes_since_cleanup += 1
    if _cache_writes_since_cleanup >= CACHE_CLEANUP_WRITE_INTERVAL:
        _cleanup_persistent_cache()
        _cache_writes_since_cleanup = 0


def _cleanup_persistent_cache() -> int:
    now = _current_timestamp()
    removed_rows = 0

    conn = _get_db_connection()
    cursor = conn.cursor()

    removed_rows += cursor.execute(
        "DELETE FROM pages WHERE updated_at < ?",
        (now - CACHE_TTL_SECONDS,),
    ).rowcount

    row_count = cursor.execute("SELECT COUNT(*) AS count FROM pages").fetchone()[0]
    overflow = row_count - MAX_PERSISTENT_CACHE_ROWS
    if overflow > 0:
        removed_rows += cursor.execute(
            """
            DELETE FROM pages
            WHERE rowid IN (
                SELECT rowid
                FROM pages
                ORDER BY COALESCE(last_accessed_at, updated_at, 0) ASC, rowid ASC
                LIMIT ?
            )
            """,
            (overflow,),
        ).rowcount

    conn.commit()
    conn.close()
    return removed_rows


def _is_cache_entry_stale(cached_page: sqlite3.Row, now: int) -> bool:
    updated_at = cached_page["updated_at"]
    return updated_at is not None and updated_at < now - CACHE_TTL_SECONDS


def _trim_cache(cache: Dict[Any, Any], max_size: int) -> None:
    while len(cache) > max_size:
        oldest_key = next(iter(cache))
        del cache[oldest_key]


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

    conn = _get_db_connection()
    cursor = conn.cursor()
    cached_page = _fetch_cached_page_row(cursor, page_name)
    now = _current_timestamp()
    wrote_cache = False

    if not cached_page:
        page = _get_page_cached(page_name, page_cache)
        if page is None:
            conn.close()
            link_cache[cache_key] = []
            _trim_cache(link_cache, MAX_LINK_CACHE_SIZE)
            return []
        _write_cached_page(cursor, page_name, page, now)
        conn.commit()
        cached_page = _fetch_cached_page_row(cursor, page_name)
        wrote_cache = True

    raw_edges = cached_page["links"]
    cached_value = json.loads(raw_edges)
    edge_data = _get_cached_page_edges(page_name, raw_edges, page_cache)

    if _is_cache_entry_stale(cached_page, now):
        page = _get_page_cached(page_name, page_cache)
        if page is not None:
            edge_data = {
                "links": page.links,
                "categories": page.categories,
            }
            _write_cached_page(cursor, page_name, page, now)
            wrote_cache = True
        else:
            _touch_cached_page(cursor, page_name, now)
        conn.commit()
    elif not isinstance(cached_value, dict):
        page = _get_page_cached(page_name, page_cache)
        if page is not None:
            edge_data = {
                "links": page.links,
                "categories": page.categories,
            }
            _write_cached_page(cursor, page_name, page, now)
            wrote_cache = True
        else:
            _touch_cached_page(cursor, page_name, now)
        conn.commit()
    else:
        _touch_cached_page(cursor, page_name, now)
        conn.commit()

    conn.close()
    if wrote_cache:
        _record_cache_write()

    links = edge_data["links"]
    if not ignore_categories:
        links = links + edge_data["categories"]

    filtered = [link for link in links if is_regular_page(link)]
    if page_name in filtered:
        filtered.remove(page_name)
    link_cache[cache_key] = filtered
    _trim_cache(link_cache, MAX_LINK_CACHE_SIZE)
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
        _trim_cache(embedding_cache, MAX_EMBEDDING_CACHE_SIZE)
    return embedding_cache[cache_key]

def _get_title_embedding(page_name: str, embedding_cache: EmbeddingCache) -> Embedding:
    cache_key = ("title", page_name)
    if cache_key not in embedding_cache:
        embedding_cache[cache_key] = encode_text(page_name)
        _trim_cache(embedding_cache, MAX_EMBEDDING_CACHE_SIZE)
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