from langid.langid import LanguageIdentifier
from langid.langid import model
from stop_words import LANGUAGE_MAPPING

from .logger import log

langid2nltk_dict: dict[str, str] = {"de": "german", "en": "english"}
# TODO: output of one lib does not fit into others
#   for nltk see https://pypi.org/project/stop-words/
#   tesseract is even stranger

langid2tesseract_dict: dict[str, str] = {"de": "deu", "en": "eng"}

lang_id = LanguageIdentifier.from_modelstring(model, norm_probs=True)


def detect_lang(txt: str) -> str | None:
    try:
        lang = lang_id.classify(txt)
    except KeyError:
        return None

    if lang[0] not in LANGUAGE_MAPPING:
        log.warning(f"\t-> WARNING: detected an unknown language: {lang}")
        return None
    log.debug(f"\t-> detected language: {lang}")
    return lang[0]


def langid2nltk(lang: str) -> str:
    return LANGUAGE_MAPPING.get(lang, "english")


def langid2tesseract(lang_ids: str | list[str]) -> str:
    langs = lang_ids
    if isinstance(langs, str):
        langs = [langs]
    if isinstance(langs, list):
        langs = [langid2tesseract_dict[lang] for lang in langs if lang in langid2tesseract_dict]
    if len(langs) < 1:
        log.warning(f"\t-> WARNING: unsupported languages detected ({lang_ids}), will enable all")
        langs = list(langid2tesseract_dict.values())
    return "+".join(langs)
