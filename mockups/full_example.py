import datetime
import time

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub
from ollama import Client

ollama_client = Client(host='http://192.168.12.177:11434')


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")


def translate_text(text):
    if not text.strip():
        return text

    response = ollama_client.chat(
        model='gemma3',
        messages=[
            {'role': 'system',
             'content': 'You are a translator. Translate the following English text to Turkish. Only provide the translation, no extra notes.'},
            {'role': 'user', 'content': text},
        ]
    )
    print(f"\n[{ts()}]")
    print(f"\t\t {text}")
    print(f"\t\t {response['message']['content']}")
    time.sleep(2)
    return response['message']['content']


def translate_epub(input_path, output_path):
    # 1. Load the original EPUB
    book = epub.read_epub(input_path)

    # 2. Iterate through all items (chapters, sections, etc.)
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Parse the HTML content
            soup = BeautifulSoup(item.get_content(), 'html.parser')

            # 3. Find and translate text nodes to preserve tag structure
            # We use string=True to target text without breaking the <div> or <p> tags
            for text_node in soup.find_all(string=True):
                if text_node.parent.name not in ['script', 'style']:  # Avoid translating code
                    original_text = text_node.strip()
                    if len(original_text) > 1:
                        translated = translate_text(original_text)
                        text_node.replace_with(translated)

            # Update the item with the new translated HTML
            item.set_content(soup.encode())

    # 4. Save the new EPUB
    epub.write_epub(output_path, book)
    print(f"Translation complete! Saved to: {output_path}")


# Run the translation
translate_epub("../epubs/unprocessed/shelley-frankenstein.epub", "./epubs/tr_shelley-frankenstein.epub")
