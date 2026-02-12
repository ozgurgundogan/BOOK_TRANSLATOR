import datetime
import os
import random
import re
import time
import uuid

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub
from ollama import Client
from tenacity import retry, stop_after_attempt, wait_exponential

from colorful_print import ptbe

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
        return original_text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
       retry_error_callback=reset_wifi_and_one_more_try)
def translate_text(text):
    if not text.strip():
        return text

    random_integer = random.randint(1, 10)
    if random_integer < 2:
        return ollama_call(text)
    else:
        return text


def sanitize_id(id_str):
    if not id_str:
        return f"id_{uuid.uuid4().hex[:6]}"
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', id_str)
    if clean[0].isdigit():
        clean = f"id_{clean}"
    return clean


def process_html_content(html_content, translation_map, item_title):
    soup = BeautifulSoup(html_content, 'html.parser')

    # FIX RSC-017: Ensure Title exists
    if not soup.title:
        title_tag = soup.new_tag("title")
        title_tag.string = str(item_title) if item_title else "Chapter"
        if soup.head:
            soup.head.insert(0, title_tag)
        else:
            head = soup.new_tag("head")
            head.append(title_tag)
            if soup.html:
                soup.html.insert(0, head)

    for text_node in soup.find_all(string=True):
        if text_node.parent.name in ['script', 'style', 'head', 'title', 'meta']:
            continue
        original_text = text_node.get_text()
        if len(original_text.strip()) <= 1:
            continue

        sentences = re.split(r'(?<=[.!?]) +', original_text.replace('\n', ' '))
        translated = []
        for s in sentences:
            clean = s.strip()
            if not clean:
                continue
            if clean not in translation_map:
                translation_map[clean] = translate_text(clean)
            translated.append(translation_map[clean])
        text_node.replace_with(" ".join(translated))

    return soup.encode(formatter="html")


def translate_epub_to_new_file(input_path, output_path):
    old_book = epub.read_epub(input_path)
    new_book = epub.EpubBook()
    item_mapping = {}
    translation_cache = {}

    # Metadata
    title_meta = old_book.get_metadata('DC', 'title')
    new_book.set_title(title_meta[0][0] if title_meta else "Translated Book")
    new_book.set_language('en')
    new_book.set_identifier(str(uuid.uuid4()))

    # 1. First Pass: Add all NON-DOCUMENT items (Fixes RSC-007)
    # We must add images and styles FIRST so document links work
    for item in old_book.get_items():
        if item.get_type() in [ebooklib.ITEM_IMAGE, ebooklib.ITEM_STYLE, ebooklib.ITEM_FONT]:
            new_asset = epub.EpubItem(
                uid=sanitize_id(item.id),
                file_name=item.file_name,  # Keeps "EPUB/epubbooks-cover.jpg" intact
                media_type=item.media_type,
                content=item.get_content()
            )
            new_book.add_item(new_asset)
            item_mapping[item.id] = new_asset

    # 2. Second Pass: Process Documents
    for item in old_book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            safe_id = sanitize_id(item.id)
            new_content = process_html_content(item.get_content(), translation_cache, item.title)

            new_item = epub.EpubHtml(
                title=item.title if item.title else "Chapter",
                file_name=item.file_name,
                content=new_content,
                uid=safe_id
            )
            new_book.add_item(new_item)
            item_mapping[item.id] = new_item

    # 3. Rebuild TOC
    def rebuild_toc(toc_list):
        new_toc = []
        for entry in toc_list:
            if isinstance(entry, epub.Link):
                new_toc.append(epub.Link(entry.href, entry.title, sanitize_id(entry.uid)))
            elif isinstance(entry, tuple) and len(entry) == 2:
                section_obj, sub_items = entry
                if isinstance(section_obj, epub.Section):
                    section_obj.uid = sanitize_id(getattr(section_obj, 'uid', None))
                new_toc.append((section_obj, rebuild_toc(sub_items)))
        return new_toc

    new_book.toc = rebuild_toc(old_book.toc)

    # 4. Rebuild Spine
    new_spine = []
    for entry in old_book.spine:
        eid = entry[0] if isinstance(entry, tuple) else entry
        if eid in item_mapping:
            new_spine.append(item_mapping[eid])
        else:
            new_spine.append(eid)
    new_book.spine = new_spine

    new_book.add_item(epub.EpubNcx())
    new_book.add_item(epub.EpubNav())
    epub.write_epub(output_path, new_book)


translate_epub_to_new_file("../epubs/unprocessed/austen-pride-and-prejudice-illustrations.epub",
                           "./epubs/trans_austen-pride-and-prejudice-illustrations.epub")
