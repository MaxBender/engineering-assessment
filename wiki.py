import wikipedia # https://wikipedia.readthedocs.io/en/latest/code.html#api
import json
import sqlite3
import spacy
from sklearn.metrics.pairwise import cosine_similarity

MAX_PATH_LENGTH = 20
MAX_SEARCH_STEPS = 100
MAX_BRANCHES_PER_PAGE = 5

# Load spacy model once at module level
nlp = spacy.load("en_core_web_sm")

# create the database if it doesn't exist
conn = sqlite3.connect("pages.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS pages (name TEXT, links TEXT)")
conn.commit()

def encode_text(text):
    """Encode text using spacy's sentence vectors"""
    doc = nlp(text)
    return doc.vector.reshape(1, -1)

# TODO: Returns the Python page too often.
def get_page(page_name):
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

def get_page_links_with_cache(page_name):
    return _load_page_links(page_name, {}, {})

def _get_page_cached(page_name, page_cache):
    if page_name not in page_cache:
        page_cache[page_name] = get_page(page_name)
    return page_cache[page_name]

def _load_page_links(page_name, page_cache, link_cache):
    if page_name in link_cache:
        return link_cache[page_name]

    conn = sqlite3.connect("pages.db")
    cursor = conn.cursor()
    cached_page = cursor.execute("SELECT * FROM pages WHERE name = ?", (page_name,)).fetchone()

    if not cached_page:
        page = _get_page_cached(page_name, page_cache)
        if page is None:
            conn.close()
            link_cache[page_name] = []
            return []
        links = page.links
        categories = page.categories
        cursor.execute("INSERT INTO pages (name, links) VALUES (?, ?)", (page_name, json.dumps(links + categories)))
        conn.commit()
        cached_page = cursor.execute("SELECT * FROM pages WHERE name = ?", (page_name,)).fetchone()

    conn.close()

    links = json.loads(cached_page[1])
    filtered = [link for link in links if is_regular_page(link)]
    if page_name in filtered:
        filtered.remove(page_name)
    link_cache[page_name] = filtered
    return filtered

def is_regular_page(page_name):
    if "disambiguation" in page_name: return False
    if "automatic" in page_name: return False
    if "article" in page_name: return False
    if "page" in page_name: return False
    if "identifier" in page_name: return False
    return True

# TODO: Gotta speed this up. It's OK if we don't get the shortest path, but we should get *a* path.
# TODO: Add a timeout to the search. 10 seconds?
def _get_summary_embedding(page_name, page_cache, embedding_cache):
    cache_key = ("summary", page_name)
    if cache_key not in embedding_cache:
        page = _get_page_cached(page_name, page_cache)
        if page is None or not page.summary:
            embedding_cache[cache_key] = None
        else:
            embedding_cache[cache_key] = encode_text(page.summary)
    return embedding_cache[cache_key]

def _get_title_embedding(page_name, embedding_cache):
    cache_key = ("title", page_name)
    if cache_key not in embedding_cache:
        embedding_cache[cache_key] = encode_text(page_name)
    return embedding_cache[cache_key]

def _score_candidate(page_name, target_embedding, page_cache, embedding_cache):
    candidate_embedding = _get_title_embedding(page_name, embedding_cache)
    if candidate_embedding is None or target_embedding is None:
        return float("-inf")
    return cosine_similarity(candidate_embedding, target_embedding)[0][0]

def _find_short_path(start_page_name, end_page_name, page_cache, link_cache, embedding_cache):
    """Find a valid path using a bounded greedy best-first search."""

    if start_page_name == end_page_name:
        return [start_page_name]

    target_embedding = _get_summary_embedding(end_page_name, page_cache, embedding_cache)
    if target_embedding is None:
        return None

    frontier = [(0.0, [start_page_name])]
    visited = {start_page_name}
    steps = 0

    while frontier and steps < MAX_SEARCH_STEPS:
        best_index = max(range(len(frontier)), key=lambda index: (frontier[index][0], frontier[index][1]))
        _, path = frontier.pop(best_index)
        current_page = path[-1]

        if len(path) >= MAX_PATH_LENGTH:
            steps += 1
            continue

        links = _load_page_links(current_page, page_cache, link_cache)
        if end_page_name in links:
            return path + [end_page_name]

        scored_candidates = []
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


def find_short_path(start_page,  end_page):
    page_cache = {
        start_page.title: start_page,
        end_page.title: end_page,
    }
    link_cache = {}
    embedding_cache = {}

    return _find_short_path(start_page.title, end_page.title, page_cache, link_cache, embedding_cache)