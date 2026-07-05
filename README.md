# Engineering Assessment Notes

This repository was updated to address the highest-value issues in the assessment first, then to complete the remaining high-ROI minor improvements.

## Summary

The work completed in this exercise focused on six areas:

1. Fixing biased page selection and removing the accidental overuse of `Python (programming language)`.
2. Fixing pathfinding correctness issues so returned paths are valid and unreachable cases fail cleanly.
3. Improving meta-category filtering and expanding regression coverage.
4. Adding targeted type hints and type-hint regression coverage.
5. Suppressing the reproducible runtime warning noise in the local environment.
6. Improving cache reuse across both path searches in a round.

## Changelog

### 1. Random page selection and page lookup fixes

- Removed deterministic random seeding from `main.py` so page selection is no longer forced into the same sequence every run.
- Changed `wiki.get_page()` to return `None` when a page cannot be resolved instead of silently falling back to `Python (programming language)`.
- Added retry logic for random page selection in `main.py` so invalid dictionary words are skipped until a valid page is found.
- Added a regression test to verify the game does not call `random.seed()`.
- Added a regression test to verify random selection retries invalid pages instead of accepting bad results.

### 2. Pathfinding correctness and stability fixes

- Replaced the previous recursive pseudo-bidirectional path search with a bounded greedy best-first search in `wiki.py`.
- Removed invalid path-joining behavior that could fabricate paths through unordered intersections.
- Stopped relying on the incorrect assumption that links from the destination page could be treated as backlinks.
- Added bounded exploration controls with path-length and search-step limits.
- Added per-search in-memory caches for page objects, page links, and embeddings to avoid repeated work during a single search.
- Made cached link loading tolerate unresolved pages cleanly by returning an empty link set.
- Kept the heuristic design goal intact: the search still aims to find a valid path, not necessarily the shortest path.

### 3. Game-loop error handling improvements

- Added graceful handling for `find_short_path()` returning `None`.
- Added user-facing output for missing paths: `No path found.` with a score of `0` instead of crashing during path display.
- Added graceful handling for invalid user-entered destination pages.
- When a user page cannot be resolved, the game now informs the player and returns to the play-again prompt instead of dereferencing `None`.

### 4. Meta-category filtering improvements

- Expanded `is_regular_page()` to filter more administrative and metadata-style labels.
- Added filtering for patterns such as `wikidata`, `wikipedia`, `short description`, `template:`, `help:`, and `user:`.
- Preserved thematic categories like `Fruit` and `Blue Things` so game-relevant category traversal still works.
- Added integration-style tests to verify cached page links retain valid categories and exclude meta/admin links and self-links.

### 5. Test coverage improvements

- Added tests for failed page lookup behavior.
- Added tests for retrying invalid random page choices.
- Added a test to ensure the RNG is not reseeded by the app.
- Added tests for missing-path handling in the game loop.
- Added tests for invalid user-entered pages.
- Added path-validity tests to ensure returned paths only use real transitions in the mocked graph.
- Added unreachable-path and invalid-intersection regressions for pathfinding.
- Added helper and integration tests for the expanded filtering behavior.

### 6. Type-hinting improvements

- Added pragmatic standard-library type hints to the public functions in `main.py` and `wiki.py`.
- Added explicit helper annotations for the pathfinding and cache helpers in `wiki.py`.
- Introduced readable cache aliases for page, link, and embedding dictionaries in `wiki.py`.
- Kept the annotations aligned with the actual runtime contracts established by the tests, including unresolved pages and missing paths.

### 7. Type-hint regression coverage

- Added a dedicated `test/test_type_hints.py` module.
- Added regression tests that inspect type annotations with `typing.get_type_hints()`.
- Covered public function annotations in both `main.py` and `wiki.py`.
- Covered the key helper/cache function annotations in `wiki.py`.

### 8. Warning suppression

- Investigated the warning TODO by reproducing runtime fetches through both `wiki.get_page()` and the underlying `wikipedia` library.
- Determined that the reproducible warning in this environment was not an HTML parser warning, but a local `urllib3` / `LibreSSL` warning.
- Added a narrow, early warning filter in `wiki.py` so this specific warning no longer pollutes test and runtime output.
- Preserved the rest of the warning surface instead of globally muting unrelated warnings.

### 9. Caching improvements

- Expanded the public cache API in `wiki.py` so `get_page_links_with_cache()` can reuse caller-supplied page and link caches.
- Expanded `find_short_path()` so callers can optionally supply page, link, and embedding caches.
- Updated `main.py` to create round-scoped caches once and reuse them across both the computer search and the user search.
- Added a SQLite index on `pages.name` to improve persistent cache lookups.
- Kept the change intentionally small by improving cache lifetime and reuse rather than redesigning the persistence layer.

### 10. Additional cache regression coverage

- Added tests that verify caller-supplied caches are honored by `get_page_links_with_cache()`.
- Added tests that verify repeated searches can reuse supplied caches without changing path correctness.
- Updated the type-hint regression coverage so the cache-aware public signatures remain locked in.

## Files Updated

- `main.py`
- `wiki.py`
- `test/test_type_hints.py`
- `test/test_main.py`
- `test/test_wiki.py`
- `README.md`

## Validation

The final validation run used:

```bash
python3 -m pytest
```

Latest result:

- `21 passed`
- `0 warnings`

The latest suite run completed cleanly with no warnings.

## Remaining Work

Minor TODOs not yet implemented include:

- any additional cache-layer cleanup beyond the current per-search improvements