from wiki import get_page, find_short_path
import random
import warnings
import nltk
import spacy
from typing import Any, List, Optional

MAX_DESTINATION_LOOKUP_ATTEMPTS = 3
MAX_RANDOM_PAGE_ATTEMPTS = 25

def get_random_page(common_words: List[str]) -> Any:
    attempts = min(len(common_words), MAX_RANDOM_PAGE_ATTEMPTS)
    for _ in range(attempts):
        page = get_page(random.choice(common_words))
        if page is not None:
            return page
    raise LookupError("Could not find a valid random Wikipedia page")

def print_path_result(label: str, path: Optional[List[str]]) -> int:
    print(f"{label}:")
    if path is None:
        print("No path found.")
        print("Length: 0\n")
        return 0

    print(f"\n -> ".join(path))
    print(f"Length: {len(path)}\n")
    return len(path)


def get_page_summary(page: Any, max_length: int = 500) -> str:
    try:
        summary = page.summary
    except Exception:
        return "Summary unavailable."

    if not summary:
        return "Summary unavailable."
    return f"{summary[:max_length]}..."


def normalize_page_input(user_input: str) -> str:
    return " ".join(user_input.strip().split())


def prompt_for_user_page(max_attempts: int = MAX_DESTINATION_LOOKUP_ATTEMPTS) -> Optional[Any]:
    for attempt in range(max_attempts):
        print("What would you like your page to be page?")
        user_page_name = normalize_page_input(input())

        if not user_page_name:
            print("Please enter a page name.\n")
            continue

        user_page = get_page(user_page_name)
        if user_page is not None:
            return user_page

        print("Could not find a page for that input.")
        if attempt < max_attempts - 1:
            print("Try another page name.\n")
        else:
            print()

    return None

def main() -> None:
    print("\n\n🥓 Welcome to WikiBacon! 🥓\n")
    print("In this game, we start from a random Wikipedia page, and then we compete to see who can name a page that is *farthest away* from the original page.\n")
    print("Ready to play? Hit Enter to start, or type 'q' to quit")
    cmd = input()
    if cmd == "q":
        return
    
    with open("dictionary.txt", "r") as f:
        common_words = f.read().splitlines()

    print("Enable hard mode? Type 'h' to ignore category links, or press Enter for normal mode")
    hard_mode = input().strip().lower() == "h"

    while True:
        try:
            start_page = get_random_page(common_words)
            computer_page = get_random_page(common_words)
        except LookupError:
            print("Could not find valid random pages right now. Please try again.\n")
            print("\n\nPlay again? Hit Enter for another round, or type 'q' to quit")
            cmd = input()
            if cmd == "q":
                print("\n🥓 Thanks for playing! 🥓\n")
                print("WikiBacon is not affiliated with Wikipedia or the Wikimedia Foundation. To donate to Wikipedia and support their vision of an open internet that makes games like this possible, please visit https://donate.wikimedia.org/\n")
                return
            continue

        print(f"The starting page is: {start_page.title}\n")
        print(f"Summary: {get_page_summary(start_page)}\n")

        print(f"The computer's page is: {computer_page.title}\n")
        print(f"Summary: {get_page_summary(computer_page)}\n")

        user_page = prompt_for_user_page()
        if user_page is None:
            print("\n\nPlay again? Hit Enter for another round, or type 'q' to quit")
            cmd = input()
            if cmd == "q":
                print("\n🥓 Thanks for playing! 🥓\n")
                print("WikiBacon is not affiliated with Wikipedia or the Wikimedia Foundation. To donate to Wikipedia and support their vision of an open internet that makes games like this possible, please visit https://donate.wikimedia.org/\n")
                return
            continue
        print(f"Your page is: {user_page.title}\n")
        print(f"Summary: {get_page_summary(user_page)}\n")

        print("Calculating Bacon paths...\n")

        page_cache = {
            start_page.title: start_page,
            computer_page.title: computer_page,
            user_page.title: user_page,
        }
        link_cache = {}
        embedding_cache = {}

        computer_path = find_short_path(start_page, computer_page, page_cache, link_cache, embedding_cache, hard_mode)
        computer_score = print_path_result("Computer's path", computer_path)

        user_path = find_short_path(start_page, user_page, page_cache, link_cache, embedding_cache, hard_mode)
        user_score = print_path_result("Your path", user_path)

        if computer_score > user_score:
            print("I win!")
        elif computer_score < user_score:
            print("You win!")
        else:
            print("It's a tie!")

        print("\n\nPlay again? Hit Enter for another round, or type 'q' to quit")
        cmd = input()
        if cmd == "q":
            print("\n🥓 Thanks for playing! 🥓\n")
            print("WikiBacon is not affiliated with Wikipedia or the Wikimedia Foundation. To donate to Wikipedia and support their vision of an open internet that makes games like this possible, please visit https://donate.wikimedia.org/\n")
            return

if __name__ == "__main__":
    main()