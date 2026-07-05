# WikiBacon
*Tavern Research Engineering Coding Assessment 2025*

🥓 WikiBacon is a game to find ideas that are as *unconnected* as possible. We start by picking a random Wikipedia page. Then each player picks a destination page, and the computer searches to find a path from the start page to their destination. The player with the longest path wins. So if the start page is "apple" and you pick "fruit," you will score very low, but "jet engine" or "Second French Republic" may score higher.

This repository contains a playable implementation of WikiBacon that runs but has some significant issues that need to be addressed. Your task is to work through some of the TODOs listed below.

## Setup

We always recommend setting up a virtual environment so that installing any dependencies doesn't affect your local system. Totally optional of course, sice we have no way of checking:
```bash
pyenv local 3.13
```
Install dependencies
```bash
pip3 install -r requirements.txt
```
Run the game
```bash
python main.py
```
Run the tests
```bash
pytest
```

## Assessment Overview

This assessment is designed to evaluate your technical judgment and foundational engineering skills in real-world scenarios. You'll work with code that needs improvement and design systems with multiple valid approaches. To keep the scope in check, it has a hard 2-hour time limit. 

It is designed to be completed **with** unrestricted access to the internet, IDEs, and AI tools like ChatGPT. If AI tools aren't part of your regular workflow, you may want to get familiar with one before starting. Most of the Tavern engineering team uses Cursor with Claude 4 Sonnet, but there are lots of good choices out there.

## What We're Looking For

We're evaluating your ability to:
- **Review and improve existing code** with attention to performance and maintainability
- **Make architectural decisions** when multiple valid approaches exist
- **Handle edge cases** and error scenarios effectively
- **Debug systematically** and implement robust solutions
- **Write maintainable, production-ready code**

None of the implementation details in this repo are sacrosanct, and in fact many are deliberately janky. Feel free to replace any part of the code as you do your work.

By the same token, there is more to do than can reasonably be accomplished in 2 hours. Don't try to do everything. **We are more interested in the quality of your most consequential changes than the volume of issues you address.** We are also interested in which issues you choose to prioritize. 

If you run into a dead end or try something that doesn't work out, commit your changes on a well-named branch and then check out main for a fresh start. **We are more interested in seeing approaches that were tried and failed than an empty history.** When you do resolve an issue, you can commit it directly to main. No more than up to one issue per commit please, which makes submissions easier to review.

There's no need to create a README or changelog, you can let your code and your git history speak for themselves.

## TODOs

Major:
1. We get [Python (Programming Language)](https://en.wikipedia.org/wiki/Python_(programming_language)) as a starter or destination page much more often than we should. Remove the randomizer seed in main.py:17, figure out why, and fix it.
2. Our search algorithm to find a short path and compute WikiBacon scores runs slower than we would like. We have gotten anecdotal reports of it sometimes returning paths that don't actually work. Investigate and fix. Note that, as a design decision, we're not worried about finding the absolute shortest path so long as we find *a* path, so we don't need to do, for example, an exhaustive breadth-first search.

Minor:
1. Sometimes we get HTML parser warnings, but they don't seem to affect output. If we can't eliminate them we should at least suppress.
2. Some of the Categories that pages are in make fun and thematic links, like Apples are in the Fruit category. But some are 'meta' pages that feel gamey, like "Short description is different from Wikidata." We should do a better job of filtering. Maybe we could also add a 'hard mode' that ignored categories altogether?
3. We are caching responses from Wikipedia to cut down on our API calls, but probably not optimally.
4. Team engineer Russ T. recommended adding some type hinting to make the code easier to maintain.


## Submission

To avoid any friction with GitHub permissions, this repo is distributed as a zip archive. To submit your completed assessment, commit your changes (directly to main is fine) and pack your updated directory into a zip archive with your name.
```bash
zip -r firstname_lastname.zip engineering-assessment
```
Email your zip archive to your recruiting coordinator.