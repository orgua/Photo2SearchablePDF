from rake_nltk import Rake

from .language_detection import langid2nltk


def extract_keywords(txt: str, lang_id: str) -> list[str] | None:
    try:
        rake = Rake(language=langid2nltk(lang_id), min_length=1, max_length=4)
        rake.extract_keywords_from_text(txt)
    except LookupError as e:
        import nltk

        nltk.download("stopwords")  # preload extra resources
        nltk.download("punkt_tab")
        raise RuntimeError("downloaded nltk stopwords - please run again") from e
    return rake.get_ranked_phrases()
