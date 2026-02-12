import datetime
import os
import re
import time
import json
import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub
from ollama import Client
from tenacity import retry, stop_after_attempt, wait_exponential

from colorful_print import ptyw, ptcn, ptbe

MODEL = 'gemma3'
FROM = 'English'
TO = 'Turkish'
ollama_client = Client(host='http://192.168.12.177:11434')


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")


def ollama_call(text):
    response = ollama_client.chat(
        model=MODEL,
        messages=[
            {'role': 'system',
             'content': f'You are a translator. Translate the following {FROM} text to {TO}. Only provide the translation, no extra notes.'},
            {'role': 'user', 'content': text},
        ]
    )
    ptbe(f"[{ts()}] {response['message']['content']}")
    time.sleep(3)
    return response['message']['content']


def reset_wifi_and_one_more_try(retry_state):
    os.system("networksetup -setairportpower en0 off")
    time.sleep(3)
    os.system("networksetup -setairportpower en0 on")
    time.sleep(6)
    original_text = retry_state.args[0]

    try:
        return ollama_call(original_text)
    except Exception as e:
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
       retry_error_callback=reset_wifi_and_one_more_try)
def translate_text(text):
    if not text.strip():
        return text
    return ollama_call(text)


def write_to_json_file(data, fpath):
    with open(fpath, 'w') as f:
        json.dump(data, f)


#
# def translate_epub_sentence_by_sentence(file_path, output_path):
#     """
#     Reads an EPUB file and yields its text content sentence by sentence.
#     """
#     book = epub.read_epub(file_path)
#
#     translation_map = {}
#     cnt = 0
#     for item in book.get_items():
#         if item.get_type() == ebooklib.ITEM_DOCUMENT:
#             cnt += 1
#             if cnt == 2:
#                 break
#
#             soup = BeautifulSoup(item.get_content(), 'html.parser')
#
#             for j, text_node in enumerate(soup.find_all(string=True)):
#                 print(f'j{j}')
#                 if j == 10:
#                     break
#
#                 # time.sleep(5)
#                 if text_node.parent.name not in ['script', 'style']:  # Avoid translating code
#                     original_text = text_node.get_text(separator=' ')
#
#                     if len(original_text) > 1:
#                         ptyw(original_text)
#                         translated = ""
#
#                         sentences = re.split(r'(?<=[.!?]) +', original_text.replace('\n', ' '))
#                         for sentence in sentences:
#                             clean_sentence = sentence.strip()
#                             if clean_sentence:
#                                 ptcn(f"{clean_sentence}")
#                                 translation = translate_text(clean_sentence)
#                                 translation_map[clean_sentence] = translation
#                                 translated += translation
#                         text_node.replace_with(translated)
#                     else:
#                         pass
#
#             item.set_content(soup.encode())
#
#     json_path = output_path.replace('/translations/', '/jsons/')
#     write_to_json_file(translation_map, json_path)
#     epub.write_epub(output_path, book)
#

def translate_epub_sentence_by_sentence(file_path, output_path):
    book = epub.read_epub(file_path)
    epub.write_epub(output_path, book)
    translation_map = {}

    # # Iterate through all documents (chapters, title page, etc.)
    # for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
    #     soup = BeautifulSoup(item.get_content(), 'html.parser')
    #
    #     # Identify tags containing translatable text while ignoring non-text areas
    #     # Iterate through NavigableStrings to preserve nested tags (<a>, <i>, etc.)
    #     for text_node in soup.find_all(string=True):
    #         if text_node.parent.name in ['script', 'style', 'head', 'title']:
    #             continue
    #
    #         original_text = str(text_node).strip()
    #         if not original_text or len(original_text) < 2:
    #             continue
    #
    #         # Split into sentences using a basic regex (better to use nltk if available)
    #         # Use (?<=[.!?]) to split after punctuation followed by a space
    #         sentences = re.split(r'(?<=[.!?])\s+', original_text)
    #         translated_sentences = []
    #
    #         for sentence in sentences:
    #             clean_sentence = sentence.strip()
    #             if not clean_sentence:
    #                 continue
    #
    #             # Cache lookup to save API costs and time
    #             if clean_sentence not in translation_map:
    #                 translation_map[clean_sentence] = translate_text(clean_sentence)
    #
    #             translated_sentences.append(translation_map[clean_sentence])
    #
    #         # Replace the text content of the node without deleting the node itself
    #         # This preserves the surrounding HTML tag structure
    #         new_text = " ".join(translated_sentences)
    #         text_node.replace_with(new_text)
    #
    #     # Re-encode the content for the EPUB item
    #     item.set_content(soup.encode(formatter="html"))
    #
    # # Save translation log
    # json_path = output_path.replace('.epub', '.json')
    # with open(json_path, 'w', encoding='utf-8') as f:
    #     json.dump(translation_map, f, ensure_ascii=False, indent=4)

    # Write the modified book to file
    epub.write_epub(output_path, book)


if __name__ == '__main__':
    # reset_wifi()
    translate_epub_sentence_by_sentence(f"./epubs/shelley-frankenstein.epub",
                                        f"./translations/shelley-frankenstein_{FROM}_{TO}_{MODEL}.epub")
