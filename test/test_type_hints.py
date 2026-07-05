from typing import Any, Dict, List, Optional, Tuple, get_type_hints

import main
import wiki


def test_main_function_type_hints():
    random_page_hints = get_type_hints(main.get_random_page)
    assert random_page_hints == {
        "common_words": List[str],
        "return": Any,
    }

    path_result_hints = get_type_hints(main.print_path_result)
    assert path_result_hints == {
        "label": str,
        "path": Optional[List[str]],
        "return": int,
    }

    main_hints = get_type_hints(main.main)
    assert main_hints == {"return": type(None)}


def test_wiki_public_function_type_hints():
    get_page_hints = get_type_hints(wiki.get_page)
    assert get_page_hints == {
        "page_name": str,
        "return": Optional[Any],
    }

    links_hints = get_type_hints(wiki.get_page_links_with_cache)
    assert links_hints == {
        "page_name": str,
        "return": List[str],
    }

    page_filter_hints = get_type_hints(wiki.is_regular_page)
    assert page_filter_hints == {
        "page_name": str,
        "return": bool,
    }

    path_hints = get_type_hints(wiki.find_short_path)
    assert path_hints == {
        "start_page": Any,
        "end_page": Any,
        "return": Optional[List[str]],
    }


def test_wiki_helper_type_hints():
    page_cache = Dict[str, Optional[Any]]
    link_cache = Dict[str, List[str]]
    embedding_cache = Dict[Tuple[str, str], Optional[Any]]

    cached_page_hints = get_type_hints(wiki._get_page_cached)
    assert cached_page_hints == {
        "page_name": str,
        "page_cache": page_cache,
        "return": Optional[Any],
    }

    load_links_hints = get_type_hints(wiki._load_page_links)
    assert load_links_hints == {
        "page_name": str,
        "page_cache": page_cache,
        "link_cache": link_cache,
        "return": List[str],
    }

    summary_hints = get_type_hints(wiki._get_summary_embedding)
    assert summary_hints == {
        "page_name": str,
        "page_cache": page_cache,
        "embedding_cache": embedding_cache,
        "return": Optional[Any],
    }

    title_hints = get_type_hints(wiki._get_title_embedding)
    assert title_hints == {
        "page_name": str,
        "embedding_cache": embedding_cache,
        "return": Any,
    }

    score_hints = get_type_hints(wiki._score_candidate)
    assert score_hints == {
        "page_name": str,
        "target_embedding": Optional[Any],
        "page_cache": page_cache,
        "embedding_cache": embedding_cache,
        "return": float,
    }

    search_hints = get_type_hints(wiki._find_short_path)
    assert search_hints == {
        "start_page_name": str,
        "end_page_name": str,
        "page_cache": page_cache,
        "link_cache": link_cache,
        "embedding_cache": embedding_cache,
        "return": Optional[List[str]],
    }