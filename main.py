from wiki import get_page, find_short_path
import random
import warnings
import nltk
import spacy
from typing import Any, List, Optional

def get_random_page(common_words: List[str]) -> Any:
    for _ in range(len(common_words)):
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

def main() -> None:
    print("\n\n🥓 Welcome to WikiBacon! 🥓\n")
    print("In this game, we start from a random Wikipedia page, and then we compete to see who can name a page that is *farthest away* from the original page.\n")
    print("Ready to play? Hit Enter to start, or type 'q' to quit")
    cmd = input()
    if cmd == "q":
        return
    
    with open("dictionary.txt", "r") as f:
        common_words = f.read().splitlines()

    while True:

        start_page = get_random_page(common_words)
        print(f"The starting page is: {start_page.title}\n")
        print(f"Summary: {start_page.summary[:500]}...\n")

        computer_page = get_random_page(common_words)

        print(f"The computer's page is: {computer_page.title}\n")
        print(f"Summary: {computer_page.summary[:500]}...\n")

        print("What would you like your page to be page?")
        user_page_name = input()
        user_page = get_page(user_page_name)
        if user_page is None:
            print("Could not find a page for that input.\n")
            print("\n\nPlay again? Hit Enter for another round, or type 'q' to quit")
            cmd = input()
            if cmd == "q":
                print("\n🥓 Thanks for playing! 🥓\n")
                print("WikiBacon is not affiliated with Wikipedia or the Wikimedia Foundation. To donate to Wikipedia and support their vision of an open internet that makes games like this possible, please visit https://donate.wikimedia.org/\n")
                return
            continue
        print(f"Your page is: {user_page.title}\n")
        print(f"Summary: {user_page.summary[:500]}...\n")

        print("Calculating Bacon paths...\n")

        computer_path = find_short_path(start_page, computer_page)
        computer_score = print_path_result("Computer's path", computer_path)

        user_path = find_short_path(start_page, user_page)
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