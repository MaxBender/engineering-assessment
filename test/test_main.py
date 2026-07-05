import pytest
from unittest.mock import patch, MagicMock
from main import main, normalize_page_input

@pytest.fixture
def mock_wiki_functions():
    """Fixture to mock Wikipedia-related functions"""
    with patch('main.get_page') as mock_get_page, \
         patch('main.find_short_path') as mock_find_path:
        
        # Create mock page
        mock_page = MagicMock()
        mock_page.title = "Test Page"
        mock_page.summary = "Test summary"
        mock_get_page.return_value = mock_page
        
        # Create mock path
        mock_find_path.return_value = ["Start", "End"]
        
        yield {
            'get_page': mock_get_page,
            'find_short_path': mock_find_path
        }

@pytest.fixture
def mock_input():
    """Fixture to mock input function"""
    with patch('builtins.input') as mock_input_func:
        yield mock_input_func


def test_main_single_round(mock_wiki_functions, mock_input):
    """Test main function for a single round"""
    # Set up input to play one round then exit
    mock_input.side_effect = ['', '', 'Ocean', 'q']
    
    main()
    
    assert mock_input.call_count == 4

def test_main_multiple_rounds(mock_wiki_functions, mock_input):
    """Test main function with custom input sequence"""
    # Simulate user entering different pages
    mock_input.side_effect = ['', '', 'Mountain', '', 'River', '', 'Plain', 'q']
    
    main()
    
    # Should have 6 input calls: 
    # enter
    # page name, play again (yes), 
    # page name, play again (yes), 
    # page name, play again (no)
    assert mock_input.call_count == 8

def test_stop_q(mock_wiki_functions, mock_input):
    """Test that main function handles different input types"""
    # Test with different input types
    test_inputs = ['q']
    
    for test_input in test_inputs:
        mock_input.reset_mock()
        mock_input.side_effect = ['', '', 'Forest', test_input, 'Utopia', 'n']
        
        # Should not raise any exceptions
        main()
        
        assert mock_input.call_count == 4

def test_main_retries_invalid_random_pages(mock_wiki_functions, mock_input):
    """Test that main retries random words until they resolve to pages."""
    valid_page = MagicMock()
    valid_page.title = "Valid Page"
    valid_page.summary = "Valid summary"

    user_page = MagicMock()
    user_page.title = "Ocean"
    user_page.summary = "Ocean summary"

    mock_wiki_functions['get_page'].side_effect = [
        None,
        valid_page,
        None,
        valid_page,
        user_page,
    ]

    mock_input.side_effect = ['', '', 'Ocean', 'q']

    with patch('main.random.choice', side_effect=['bad-start', 'good-start', 'bad-computer', 'good-computer']):
        main()

    assert mock_wiki_functions['get_page'].call_args_list[0].args == ('bad-start',)
    assert mock_wiki_functions['get_page'].call_args_list[1].args == ('good-start',)
    assert mock_wiki_functions['get_page'].call_args_list[2].args == ('bad-computer',)
    assert mock_wiki_functions['get_page'].call_args_list[3].args == ('good-computer',)

def test_main_does_not_seed_random(mock_wiki_functions, mock_input):
    """Test that the game does not force deterministic random choices."""
    mock_input.side_effect = ['', '', 'Ocean', 'q']

    with patch('main.random.seed') as mock_seed, \
         patch('main.random.choice', side_effect=['start-word', 'computer-word']):
        main()

    mock_seed.assert_not_called()

def test_main_handles_missing_paths(mock_wiki_functions, mock_input, capsys):
    """Test that the game handles missing paths without crashing."""
    mock_input.side_effect = ['', '', 'Ocean', 'q']
    mock_wiki_functions['find_short_path'].side_effect = [None, ['Start', 'End']]

    main()

    output = capsys.readouterr().out
    assert "No path found." in output
    assert "Length: 0" in output

def test_main_handles_invalid_user_page(mock_wiki_functions, mock_input, capsys):
    """Test that repeated invalid user pages do not crash the game."""
    mock_input.side_effect = ['', '', 'NotARealPage', 'StillNotReal', 'NopeAgain', 'q']
    mock_wiki_functions['get_page'].side_effect = [
        mock_wiki_functions['get_page'].return_value,
        mock_wiki_functions['get_page'].return_value,
        None,
        None,
        None,
    ]

    main()

    output = capsys.readouterr().out
    assert "Could not find a page for that input." in output
    assert output.count("Could not find a page for that input.") == 3


def test_main_retries_then_accepts_valid_user_page(mock_wiki_functions, mock_input, capsys):
    """Test that user destination input is retried until a valid page is found."""
    valid_page = MagicMock()
    valid_page.title = "Ocean"
    valid_page.summary = "Ocean summary"

    mock_input.side_effect = ['', '', 'bad-page', 'Ocean', 'q']
    mock_wiki_functions['get_page'].side_effect = [
        mock_wiki_functions['get_page'].return_value,
        mock_wiki_functions['get_page'].return_value,
        None,
        valid_page,
    ]

    main()

    output = capsys.readouterr().out
    assert "Try another page name." in output
    assert "Your page is: Ocean" in output


def test_main_normalizes_user_page_input(mock_wiki_functions, mock_input):
    """Test that user page lookup receives normalized input."""
    mock_input.side_effect = ['', '', '  Nintendo    Switch   2  ', 'q']

    main()

    user_lookup_call = mock_wiki_functions['get_page'].call_args_list[2]
    assert user_lookup_call.args == ('Nintendo Switch 2',)


def test_normalize_page_input():
    assert normalize_page_input("  Nintendo    Switch   2  ") == "Nintendo Switch 2"
    assert normalize_page_input("\t\n  ") == ""

def test_main_hard_mode_passes_flag(mock_wiki_functions, mock_input):
    """Test that hard mode selection is passed through to both path searches."""
    mock_input.side_effect = ['', 'h', 'Ocean', 'q']

    main()

    first_call = mock_wiki_functions['find_short_path'].call_args_list[0]
    second_call = mock_wiki_functions['find_short_path'].call_args_list[1]
    assert first_call.args[-1] is True
    assert second_call.args[-1] is True