"""Diagnostic script to reproduce BeautifulSoup parser warnings.

This does not run as part of the normal pytest suite. It forces the
third-party wikipedia package down its disambiguation-page parsing path,
which currently calls BeautifulSoup(html) without specifying a parser.

Run manually with:

    python3 test/diagnostic_html_parser_warning.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import warnings

from bs4 import GuessedAtParserWarning

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wiki  # noqa: F401 - imports app-local warning configuration first
import wikipedia.wikipedia as wikipedia_impl


def main() -> None:
    warnings.simplefilter("always")
    warnings.simplefilter("always", GuessedAtParserWarning)

    original_wiki_request = wikipedia_impl._wiki_request

    def fake_wiki_request(params):
        if params.get("prop") == "info|pageprops":
            return {
                "query": {
                    "pages": {
                        "123": {
                            "pageid": 123,
                            "title": "Mercury",
                            "pageprops": {"disambiguation": ""},
                        }
                    }
                }
            }

        if params.get("prop") == "revisions" and params.get("rvparse") == "":
            return {
                "query": {
                    "pages": {
                        "123": {
                            "revisions": [
                                {
                                    "*": """
                                    <ul>
                                      <li><a href='/wiki/Mercury_(planet)'>Mercury (planet)</a></li>
                                      <li><a href='/wiki/Mercury_(element)'>Mercury (element)</a></li>
                                    </ul>
                                    """
                                }
                            ]
                        }
                    }
                }
            }

        return original_wiki_request(params)

    wikipedia_impl._wiki_request = fake_wiki_request

    try:
        wikipedia_impl.page("Mercury", auto_suggest=False, redirect=False)
    except Exception as exc:
        print(type(exc).__name__, exc)
    finally:
        wikipedia_impl._wiki_request = original_wiki_request


if __name__ == "__main__":
    main()