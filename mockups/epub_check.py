from epubcheck import EpubCheck

result = EpubCheck(f"./epubs/trans_shelley-frankenstein.epub")
print(f"Is valid: {result.valid}")
if not result.valid:
    print(result.messages)  # Lists every error line-by-line
