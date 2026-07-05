import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
import wiki

# Our hill-climbing algorithm should be able to traverse across both links and categories. Because it is greedy, it should miss the shortcut through the apparently unrelated Warp Pipe pages.

# Hill-climbing path:
# Blueberry -> Apple -> Apple Computer -> Netflix -> Bridgerton (5)

# Secret shortcut path:
# Blueberry -> Mushroom Kingdom Warp Pipe -> Bowser's Castle Warp Pipe  -> Bridgerton (4)

TEST_PAGES = {
    "Blueberry": {
        "links": ["Apple", "Mushroom Kingdom Warp Pipe", "All (disambiguation)"],
        "categories": ["Fruit", "Blue Things"],
        "summary": "Blueberries are a type of fruit that are blue. They are associated with the color blue, the ocean, and the color of the sky."
    },
    "Apple": {
        "links": ["Apple Computer", "Blueberry", "All (disambiguation)"],
        "categories": ["Fruit"],
        "summary": "Apple is a delicious red fruit that grows on trees. It is associated with autumn, education, and the theory of gravity. It is also the name of a computer company."
    },
    "Apple Computer": {
        "links": ["Apple", "Netflix", "All (disambiguation)"],
        "categories": ["Technology"],
        "summary": "Apple Computer is a company that makes computers and software. Its products include desktop and laptop Macintosh computers, mobile devices like the iPhone and iPad, and the streaming service AppleTV."
    },

    "Ocean": {
        "links": ["River", "Lake", "All (disambiguation)"],
        "categories": ["Big Water", "Blue Things"],
        "summary": "The ocean is a large body of water that covers most of the Earth's surface. It is associated with the color blue, the color of the sky, and the vastness and mystery of the unknown."
    },
    "River": {
        "links": ["Ocean", "Stream", "All (disambiguation)"],
        "categories": [],
        "summary": "A river is a large body of moving water. Rivers eventually empty into the ocean. They are associated with flow, movement, and change."
    },
    "Stream": {
        "links": ["River", "Netflix", "All (disambiguation)"],
        "categories": [],
        "summary": "A stream is a small body of moving water. It is associated with movement and change. A stream is also the preferred metaphor for any continually-delivered data, especially entertainment."
    },
    "Netflix": {
        "links": ["Stream", "Apple Computer", "Bridgerton", "Bowser's Castle Warp Pipe", "All (disambiguation)"],
        "categories": [],
        "summary": "Netflix is a streaming service that delivers entertainment to your home. It is associated with streaming, entertainment, and the internet."
    },
    "Bridgerton": {
        "links": ["Netflix", "All (disambiguation)"],
        "categories": [],
        "summary": "Bridgerton is a streaming drama that plays on Netflix.",
    },
    "Mushroom Kingdom Warp Pipe": {
        "links": ["Blueberry", "Bowser's Castle Warp Pipe", "All (disambiguation)"],
        "categories": [],
        "summary": "Doot-doot doot-doot doot-doot"
    },
    "Bowser's Castle Warp Pipe": {
        "links": ["Netflix", "Mushroom Kingdom Warp Pipe", "All (disambiguation)"],
        "categories": [],
        "summary": "Doot-doot doot-doot doot-doot"
    },
    "Fruit": {
        "links": ["Apple", "Blueberry", "All (disambiguation)"],
        "categories": [],
        "summary": "Fruit is a type of food that is grown on trees. It is associated with the color red, the color of the sky, and the vastness and mystery of the unknown."
    },
    "Blue Things": {
        "links": ["Blueberry", "Ocean", "All (disambiguation)"],
        "categories": [],
        "summary": "Blue Things are a type of thing that are blue. They are associated with the color blue, the ocean, and the color of the sky."
    },
    "Orphan (graph theory)": {
        "links": ["All (disambiguation)", "Orphan (graph theory)"],
        "categories": [],
        "summary": "This page is orphaned. It is not linked to by any other pages."
    },
    "All (disambiguation)": {
        "links": ["Apple", "Blueberry", "Ocean", "River", "Stream", "Netflix", "Bridgerton", "Mushroom Kingdom Warp Pipe", "Bowser's Castle Warp Pipe", "Orphan (graph theory)"],
        "categories": [],
        "summary": "All is a disambiguation page. Do not use it for pathfinding."
    },
    "Python (programming language)": {
        "links": ["Apple", "All (disambiguation)"],
        "categories": [],
        "summary": "Python is a programming language."
    },
    "Start Node": {
        "links": ["Bridge Node", "All (disambiguation)"],
        "categories": [],
        "summary": "A starting point that only points to a bridge node."
    },
    "Bridge Node": {
        "links": ["Detour Node", "All (disambiguation)"],
        "categories": [],
        "summary": "A bridge node that does not actually lead to the target page."
    },
    "Detour Node": {
        "links": ["Bridge Node", "All (disambiguation)"],
        "categories": [],
        "summary": "A detour node that cycles away from the target."
    },
    "Target Node": {
        "links": ["Elsewhere Node", "All (disambiguation)"],
        "categories": ["Bridge Node"],
        "summary": "A target node whose category mentions the bridge node without a valid reverse edge."
    },
    "Elsewhere Node": {
        "links": ["Target Node", "All (disambiguation)"],
        "categories": [],
        "summary": "An unrelated node connected only to the target node."
    },
    "Filtering Source": {
        "links": ["Apple", "Template:Stub", "Help:Contents", "Filtering Source"],
        "categories": [
            "Fruit",
            "Short description is different from Wikidata",
            "Wikipedia articles needing cleanup",
        ],
        "summary": "A page used to verify category and link filtering behavior."
    }
}

def assert_valid_path(path):
    assert path is not None
    for current_page, next_page in zip(path, path[1:]):
        current_data = TEST_PAGES[current_page]
        valid_transitions = current_data["links"] + current_data["categories"]
        assert next_page in valid_transitions


@pytest.fixture(autouse=True)
def isolated_cache_db(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki, "CACHE_DB_PATH", str(tmp_path / "pages.db"))
    monkeypatch.setattr(wiki, "_cache_writes_since_cleanup", 0)


def fetch_cache_rows():
    conn = sqlite3.connect(wiki.CACHE_DB_PATH)
    rows = conn.execute(
        "SELECT name, links, updated_at, last_accessed_at FROM pages ORDER BY name"
    ).fetchall()
    conn.close()
    return rows

@pytest.fixture
def mock_wikipedia_library():
    """Fixture to mock both get_page and get_page_links_with_cache"""
    mock_pages = {}
    for page_name, page_data in TEST_PAGES.items():
        mock_page = MagicMock()
        mock_page.title = page_name
        mock_page.summary = page_data["summary"]
        mock_page.links = page_data["links"]
        mock_page.categories = page_data["categories"]
        mock_pages[page_name] = mock_page

    with patch('wikipedia.page') as mock_page:
        mock_page.side_effect = lambda page_name, **kwargs: mock_pages[page_name]
        yield mock_page

def test_get_page(mock_wikipedia_library):
    """Test get_page function"""
    page = wiki.get_page("Apple")
    assert page.title == "Apple"
    assert page.summary == TEST_PAGES["Apple"]["summary"]
    assert page.links == TEST_PAGES["Apple"]["links"]
    assert page.categories == TEST_PAGES["Apple"]["categories"]

def test_get_page_search(mock_wikipedia_library):
    with patch('wikipedia.search') as mock_search:
        mock_search.return_value = []
        page = wiki.get_page("Appl")
        assert page is None

        mock_search.return_value = ["Apple"]
        page = wiki.get_page("Appl")
        assert page.title == "Apple"

def test_is_regular_page_allows_thematic_categories():
    assert wiki.is_regular_page("Fruit") is True
    assert wiki.is_regular_page("Blue Things") is True

def test_is_regular_page_filters_meta_categories():
    assert wiki.is_regular_page("Short description is different from Wikidata") is False
    assert wiki.is_regular_page("Wikipedia articles needing cleanup") is False
    assert wiki.is_regular_page("Template:Stub") is False
    assert wiki.is_regular_page("Help:Contents") is False
    assert wiki.is_regular_page("User:Example") is False

def test_get_page_links_with_cache_filters_meta_categories(mock_wikipedia_library):
    links = wiki.get_page_links_with_cache("Filtering Source")

    assert "Apple" in links
    assert "Fruit" in links
    assert "Template:Stub" not in links
    assert "Help:Contents" not in links
    assert "Short description is different from Wikidata" not in links
    assert "Wikipedia articles needing cleanup" not in links
    assert "Filtering Source" not in links

def test_get_page_links_with_cache_can_ignore_categories(mock_wikipedia_library):
    links = wiki.get_page_links_with_cache("Filtering Source", ignore_categories=True)

    assert "Apple" in links
    assert "Fruit" not in links
    assert "Short description is different from Wikidata" not in links

def test_get_page_links_with_cache_uses_supplied_caches(mock_wikipedia_library):
    page_cache = {}
    link_cache = {}

    links = wiki.get_page_links_with_cache("Filtering Source", page_cache, link_cache)

    assert link_cache[("Filtering Source", False)] == links
    if "Filtering Source" in page_cache:
        assert page_cache["Filtering Source"].title == "Filtering Source"

    second_links = wiki.get_page_links_with_cache("Filtering Source", page_cache, link_cache)
    assert second_links == links
    assert len(link_cache) == 1


def test_cache_schema_bootstrap_migrates_existing_database(mock_wikipedia_library):
    conn = sqlite3.connect(wiki.CACHE_DB_PATH)
    conn.execute("CREATE TABLE pages (name TEXT, links TEXT)")
    conn.execute(
        "INSERT INTO pages (name, links) VALUES (?, ?)",
        ("Filtering Source", json.dumps(TEST_PAGES["Filtering Source"]["links"])),
    )
    conn.commit()
    conn.close()

    links = wiki.get_page_links_with_cache("Filtering Source")

    conn = sqlite3.connect(wiki.CACHE_DB_PATH)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(pages)").fetchall()}
    row = conn.execute(
        "SELECT links, updated_at, last_accessed_at FROM pages WHERE name = ?",
        ("Filtering Source",),
    ).fetchone()
    conn.close()

    assert "Fruit" in links
    assert {"updated_at", "last_accessed_at"}.issubset(columns)
    assert json.loads(row[0]) == {
        "links": TEST_PAGES["Filtering Source"]["links"],
        "categories": TEST_PAGES["Filtering Source"]["categories"],
    }
    assert row[1] is not None
    assert row[2] is not None


def test_stale_cache_entry_refreshes_before_use(mock_wikipedia_library, monkeypatch):
    now = 10_000
    monkeypatch.setattr(wiki, "CACHE_TTL_SECONDS", 60)
    monkeypatch.setattr(wiki, "_current_timestamp", lambda: now)

    conn = wiki._get_db_connection()
    conn.execute(
        """
        INSERT INTO pages (name, links, updated_at, last_accessed_at)
        VALUES (?, ?, ?, ?)
        """,
        ("Blueberry", json.dumps({"links": ["Apple"], "categories": []}), now - 600, now - 600),
    )
    conn.commit()
    conn.close()

    links = wiki.get_page_links_with_cache("Blueberry")
    rows = fetch_cache_rows()
    blueberry_row = next(row for row in rows if row[0] == "Blueberry")

    assert "Blue Things" in links
    assert json.loads(blueberry_row[1]) == {
        "links": TEST_PAGES["Blueberry"]["links"],
        "categories": TEST_PAGES["Blueberry"]["categories"],
    }
    assert blueberry_row[2] == now
    assert blueberry_row[3] == now


def test_stale_cache_entry_falls_back_to_cached_edges_when_refresh_fails(monkeypatch):
    now = 20_000
    monkeypatch.setattr(wiki, "CACHE_TTL_SECONDS", 60)
    monkeypatch.setattr(wiki, "_current_timestamp", lambda: now)

    conn = wiki._get_db_connection()
    conn.execute(
        """
        INSERT INTO pages (name, links, updated_at, last_accessed_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            "Filtering Source",
            json.dumps({"links": ["Apple", "Template:Stub"], "categories": ["Fruit"]}),
            now - 600,
            now - 600,
        ),
    )
    conn.commit()
    conn.close()

    with patch.object(wiki, "get_page", return_value=None):
        links = wiki.get_page_links_with_cache("Filtering Source")

    rows = fetch_cache_rows()
    filtering_row = next(row for row in rows if row[0] == "Filtering Source")

    assert links == ["Apple", "Fruit"]
    assert json.loads(filtering_row[1]) == {
        "links": ["Apple", "Template:Stub"],
        "categories": ["Fruit"],
    }
    assert filtering_row[2] == now - 600
    assert filtering_row[3] == now


def test_cleanup_prunes_oldest_persistent_rows(monkeypatch):
    now = 50_000
    monkeypatch.setattr(wiki, "CACHE_TTL_SECONDS", 10_000)
    monkeypatch.setattr(wiki, "MAX_PERSISTENT_CACHE_ROWS", 2)
    monkeypatch.setattr(wiki, "_current_timestamp", lambda: now)

    conn = wiki._get_db_connection()
    for name, last_accessed_at in [("Apple", 100), ("Blueberry", 200), ("Ocean", 300), ("River", 400)]:
        conn.execute(
            """
            INSERT INTO pages (name, links, updated_at, last_accessed_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, json.dumps({"links": ["Stream"], "categories": []}), now, last_accessed_at),
        )
    conn.commit()
    conn.close()

    removed_rows = wiki._cleanup_persistent_cache()
    remaining_names = [row[0] for row in fetch_cache_rows()]

    assert removed_rows == 2
    assert remaining_names == ["Ocean", "River"]


def test_link_cache_is_trimmed_to_max_size(mock_wikipedia_library, monkeypatch):
    monkeypatch.setattr(wiki, "MAX_LINK_CACHE_SIZE", 2)

    link_cache = {}
    wiki.get_page_links_with_cache("Blueberry", link_cache=link_cache)
    wiki.get_page_links_with_cache("Apple", link_cache=link_cache)
    wiki.get_page_links_with_cache("Ocean", link_cache=link_cache)

    assert len(link_cache) == 2
    assert ("Blueberry", False) not in link_cache
    assert ("Apple", False) in link_cache
    assert ("Ocean", False) in link_cache


def test_embedding_cache_is_trimmed_to_max_size(monkeypatch):
    monkeypatch.setattr(wiki, "MAX_EMBEDDING_CACHE_SIZE", 2)

    embedding_cache = {}
    with patch.object(wiki, "encode_text", side_effect=lambda text: text):
        wiki._get_title_embedding("Apple", embedding_cache)
        wiki._get_title_embedding("Blueberry", embedding_cache)
        wiki._get_title_embedding("Ocean", embedding_cache)

    assert len(embedding_cache) == 2
    assert ("title", "Apple") not in embedding_cache
    assert ("title", "Blueberry") in embedding_cache
    assert ("title", "Ocean") in embedding_cache

def test_find_short_path_reuses_supplied_caches(mock_wikipedia_library):
    start_page = wiki.get_page("Blueberry")
    end_page = wiki.get_page("Ocean")

    page_cache = {
        start_page.title: start_page,
        end_page.title: end_page,
    }
    link_cache = {}
    embedding_cache = {}

    first_path = wiki.find_short_path(start_page, end_page, page_cache, link_cache, embedding_cache)
    cache_sizes = (len(page_cache), len(link_cache), len(embedding_cache))

    second_path = wiki.find_short_path(start_page, end_page, page_cache, link_cache, embedding_cache)

    assert first_path == ["Blueberry", "Blue Things", "Ocean"]
    assert second_path == first_path
    assert (len(page_cache), len(link_cache), len(embedding_cache)) == cache_sizes

def test_link_through_categories(mock_wikipedia_library):
    start_page = wiki.get_page("Blueberry")
    end_page = wiki.get_page("Ocean")
    path = wiki.find_short_path(start_page, end_page)
    # Finds the path through the "Blue Things" category
    assert path == ["Blueberry", "Blue Things", "Ocean"]
    assert_valid_path(path)

def test_hard_mode_ignores_category_shortcuts(mock_wikipedia_library):
    start_page = wiki.get_page("Blueberry")
    end_page = wiki.get_page("Ocean")
    path = wiki.find_short_path(start_page, end_page, ignore_categories=True)

    assert path == ["Blueberry", "Apple", "Apple Computer", "Netflix", "Stream", "River", "Ocean"]
    assert_valid_path(path)

def test_do_not_link_through_meta_pages(mock_wikipedia_library):
    start_page = wiki.get_page("Apple")
    end_page = wiki.get_page("Orphan (graph theory)")
    path = wiki.find_short_path(start_page, end_page)
    assert path is None

def test_greedy_search(mock_wikipedia_library):
    start_page = wiki.get_page("Blueberry")
    end_page = wiki.get_page("Bridgerton")
    path = wiki.find_short_path(start_page, end_page)
    print(path)
    # Doesn't find the shortcut through the Warp Pipes, because it's greedy
    assert path == ["Blueberry", "Apple", "Apple Computer", "Netflix", "Bridgerton"]
    assert_valid_path(path)

def test_do_not_return_invalid_intersection_path(mock_wikipedia_library):
    start_page = wiki.get_page("Start Node")
    end_page = wiki.get_page("Target Node")

    path = wiki.find_short_path(start_page, end_page)

    assert path is None
