import os
import colorama
from colorama import Fore, Style

from rich.console import Console
from rich.markdown import Markdown


def print_markdown(markdown_text):
    console = Console()
    md = Markdown(markdown_text)
    print("")
    console.print(md)
    print("")


def clear_console():
    os.system("clear" if os.name == "posix" else "cls")


def text_detected(full_sentences, text):
    global displayed_text
    sentences_with_style = [
        f"{Fore.YELLOW + sentence + Style.RESET_ALL if i % 2 == 0 else Fore.CYAN + sentence + Style.RESET_ALL} "
        for i, sentence in enumerate(full_sentences)
    ]
    new_text = (
        "".join(sentences_with_style).strip() + " " + text
        if len(sentences_with_style) > 0
        else text
    )

    if new_text != displayed_text:
        displayed_text = new_text
        clear_console()
        print(displayed_text, end="\n", flush=True)


colorama.init()
