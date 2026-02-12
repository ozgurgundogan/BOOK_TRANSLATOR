import datetime
import glob
import json
import os
import re
import shutil
import time

from bs4 import BeautifulSoup
from ollama import Client
from tenacity import retry, stop_after_attempt, wait_exponential

from colorful_print import ptbe

translation_map = {}

MODEL = 'gemma3'
FROM = 'English'
TO = 'Turkish'
ollama_client = Client(host='http://192.168.12.177:11434', timeout=60)


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")


"""
    OLLAMA TRANSLATOR
"""


def ollama_call(text):
    response = ollama_client.chat(
        model=MODEL,
        messages=[
            {'role': 'system',
             'content': f'You are a translator. Translate the following {FROM} text to {TO}. Only provide the translation, no extra notes.'},
            {'role': 'user', 'content': text},
        ],
        options={
            'temperature': 0.08,  # Higher = more creative, Lower = more predictable
        }
    )
    ptbe(f"[{ts()}] {response['message']['content']}")
    time.sleep(0.1)
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
        return original_text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=6),
       retry_error_callback=reset_wifi_and_one_more_try)
def _translate_text(text):
    if not text.strip():
        return text
    return ollama_call(text)



"""
    PATH GETTERS
"""


def _get_processing_path(book_path):
    return book_path.replace("unprocessed", "processing").replace(".epub", "")


def _get_translation_maps_path(book_path):
    return book_path.replace("unprocessed", "translation_maps").replace(".epub", ".json")


def _get_translated_path(book_path):
    return book_path.replace("unprocessed", "translated")


def _get_processed_path(book_path):
    return book_path.replace("unprocessed", "processed")


"""
    EPUB PACKER
"""


def unpack_book(book_path):
    os.system(f'/Applications/calibre.app/Contents/MacOS/ebook-convert {book_path} {_get_processing_path(book_path)}')
    time.sleep(3)


def pack_book(book_path):
    os.system(
        f'/Applications/calibre.app/Contents/MacOS/ebook-convert {_get_processing_path(book_path)}/content.opf {_get_translated_path(book_path)}')
    time.sleep(3)


"""
    FOLDER ADJUSTER
"""


def move_book_to_processed_folder(book_path):
    shutil.move(book_path, _get_processed_path(book_path))


def remove_unpack_data(book_path):
    shutil.rmtree(_get_processing_path(book_path))


"""
    FILE GETTER
"""


def get_unprocessed_epubs():
    return glob.glob("./epubs/unprocessed/*.epub")


def _get_xhtml_files(book_path):
    folder_path = _get_processing_path(book_path)
    epub_files = glob.glob(f"{folder_path}/**/*.xhtml", recursive=True)
    return epub_files


def _get_ncx_files(book_path):
    folder_path = _get_processing_path(book_path)
    files = glob.glob(f"{folder_path}/**/*.ncx", recursive=True)
    return files


def _get_opf_files(book_path):
    folder_path = _get_processing_path(book_path)
    files = glob.glob(f"{folder_path}/**/*.opf", recursive=True)
    return files


def _has_any_text(tag):
    # Returns True if the tag has text and it's not just whitespace
    return tag.get_text(strip=True) != ""


def _write_to_json_file(data, fpath):
    with open(fpath, 'w') as f:
        json.dump(data, f)


"""
    EPUB PROCESSOR
"""


def _process_a_tag(tag):
    original_text = tag.get_text()
    if len(original_text.strip()) <= 1:
        return

    sentences = re.split(r'(?<=[.!?]) +', original_text.replace('\n', ' '))
    translated = []
    for s in sentences:
        clean = s.strip()
        if not clean:
            continue
        if clean not in translation_map:
            translation_map[clean] = _translate_text(clean)
        translated.append(translation_map[clean])
    tag.string = " ".join(translated)


def process_an_xhtml_file(file_path):
    print(file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    soup = BeautifulSoup(content, "xml")

    for tag in soup.find_all(_has_any_text):
        if tag.name and tag.name.lower() not in ['html', 'body', 'section']:
            if not tag.find(recursive=False):  # if there is a child tag, we will bypass so we get child only ONCE.
                _process_a_tag(tag)

    output_data = soup.encode(encoding='utf-8')
    with open(file_path, "wb") as file:
        file.write(output_data)


def translate_book(book_path):
    xhtml_files = _get_xhtml_files(book_path)
    ncx_files = _get_ncx_files(book_path)
    opf_files = _get_opf_files(book_path)
    for fl in xhtml_files:
        process_an_xhtml_file(fl)
    for fl in ncx_files:
        process_an_xhtml_file(fl)
    for fl in opf_files:
        process_an_xhtml_file(fl)


def validate_translated_book():
    os.system('java -jar ./epub_checker/epubcheck-5.3.0/epubcheck.jar ./epubs/trans_austen-pride-and-prejudice-illustrations.epub')


if __name__ == '__main__':
    unprocessed_books = get_unprocessed_epubs()
    for book_path in unprocessed_books:
        translation_map = {}
        unpack_book(book_path)
        try:
            translate_book(book_path)
            pack_book(book_path)
            move_book_to_processed_folder(book_path)
            remove_unpack_data(book_path)
        except Exception as e:
            pass
        finally:
            _write_to_json_file(translation_map, _get_translation_maps_path(book_path))
