import ollama

# The client automatically picks up the OLLAMA_HOST environment variable
from epub_reader import read_epub_sentence_by_sentence

client = ollama.Client(host='http://192.168.12.177:11434')


def english_to_turkish(english_sentence, model_name='gemma3'):
    system_prompt = (
        "You are a professional book translator specializing in English to Turkish. "
        "Only provide the translation. Do not include explanations or extra text."
    )

    try:
        response = client.chat(
            model=model_name,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f"Translate this to Turkish: {english_sentence}"},
            ],
            options={'temperature': 0.3}
        )

        return response['message']['content']

    except Exception as e:
        print(f"Error connecting to remote Ollama server: {e}")


if __name__ == '__main__':
    for sentence in read_epub_sentence_by_sentence("../epubs/shelley-frankenstein.epub"):
        if 'I am already far north of London' in sentence:
            print(sentence)
            print(english_to_turkish(sentence))
            break

    # print(english_to_turkish("I am already far north of London, and as I walk in the streets of Petersburgh, I feel a cold northern breeze play upon my cheeks, which braces my nerves and fills me with delight. "))