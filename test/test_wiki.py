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
    }
}

def assert_valid_path(path):
    assert path is not None
    for current_page, next_page in zip(path, path[1:]):
        current_data = TEST_PAGES[current_page]
        valid_transitions = current_data["links"] + current_data["categories"]
        assert next_page in valid_transitions

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

def test_link_through_categories(mock_wikipedia_library):
    start_page = wiki.get_page("Blueberry")
    end_page = wiki.get_page("Ocean")
    path = wiki.find_short_path(start_page, end_page)
    # Finds the path through the "Blue Things" category
    assert path == ["Blueberry", "Blue Things", "Ocean"]
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
