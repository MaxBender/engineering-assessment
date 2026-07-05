import wikipedia # https://wikipedia.readthedocs.io/en/latest/code.html#api
import json
import sqlite3
import spacy
from sklearn.metrics.pairwise import cosine_similarity

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
    conn = sqlite3.connect("pages.db")
    cursor = conn.cursor()
    cached_page = cursor.execute("SELECT * FROM pages WHERE name = ?", (page_name,)).fetchone()

    if not cached_page:
        page = get_page(page_name)
        links = page.links
        categories = page.categories
        cursor.execute("INSERT INTO pages (name, links) VALUES (?, ?)", (page_name, json.dumps(links + categories)))
        conn.commit()
        cached_page = cursor.execute("SELECT * FROM pages WHERE name = ?", (page_name,)).fetchone()

    links = json.loads(cached_page[1])
    filtered = [link for link in links if is_regular_page(link)]
    if page_name in filtered:
        filtered.remove(page_name)
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
def _find_short_path(start_path, end_path):
    """Quick and dirty method to find a short path between two Wikipedia pages. Hill climbs from the start and end pages towards each other, using cosine similarity of  sentence embeddings to score links. Kinda like A*, but with cosine similarity instead of Euclidean distance?"""

    start_leaf = start_path[-1]
    end_leaf = end_path[0]

    # Base cases: we've reached the end
    if len(start_path) + len(end_path) > 20:
        return None

    if start_leaf == end_leaf:
        return start_path + end_path
    
    links = get_page_links_with_cache(start_leaf)
    if end_leaf in links:
        return start_path + end_path
    
    # TODO: Check whether links are actually symmetric.
    backlinks = get_page_links_with_cache(end_leaf)
    if start_leaf in backlinks:
        return start_path + end_path
    
    intersection = list(set(links) & set(backlinks))
    if len(intersection) > 0:
        return start_path + [intersection[0]] + end_path
    
    print(f"{start_path[-1]} ??? {end_path[0]}")

    # Recursively search inwards
    end_leaf_page = get_page(end_leaf)
    end_embedding = encode_text(end_leaf_page.summary)
    scored_links = [(link, cosine_similarity(encode_text(link), end_embedding)[0][0]) for link in links]
    scored_links.sort(key=lambda x: x[1], reverse=True)
    next_page = scored_links[0][0]

    start_leaf_page = get_page(start_leaf)
    start_embedding = encode_text(start_leaf_page.summary)
    scored_categories = [(backlink, cosine_similarity(encode_text(backlink), start_embedding)[0][0]) for backlink in backlinks]
    scored_categories.sort(key=lambda x: x[1], reverse=True)
    previous_page = scored_categories[0][0]

    return _find_short_path(start_path + [next_page], [previous_page] + end_path)


def find_short_path(start_page,  end_page):
    start_path = [start_page.title]
    end_path = [end_page.title]

    return _find_short_path(start_path, end_path)