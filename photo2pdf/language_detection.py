"""Tooling around the option to detect languages.

langid uses ISO 639-1:2002 IDs
nltk wants the language-name
   see https://pypi.org/project/stop-words/
tesseract uses ISO 639-2:1998 IDs
   (similar to 639-3:2007 but the subtypes are missing in tesseract)
"""

import iso639
from langid.langid import LanguageIdentifier
from langid.langid import model
from stop_words import LANGUAGE_MAPPING

from .logger import log

lim = LanguageIdentifier.from_modelstring(model, norm_probs=True)


def is_iso639_1(id1: str) -> bool:
    try:
        iso639.Language.from_part1(id1)
    except iso639.LanguageNotFoundError:
        return False
    return True


def is_iso639_2(id2: str) -> bool:
    try:
        iso639.Language.from_part2t(id2)
    except iso639.LanguageNotFoundError:
        return False
    return True


def lang_name(ident: str) -> str:
    try:
        lang = iso639.Language.match(ident)
    except iso639.LanguageNotFoundError:
        return ""
    return lang.name


def langid2nltk(lang: str) -> str:
    return LANGUAGE_MAPPING.get(lang, "english")


def detect_lang(txt: str) -> str | None:
    """Detect language based on language model and returns ISO 639-1:2002 ID (2-letter code)."""
    if txt is None:
        return None
    try:
        id1, rank = lim.classify(txt)
        # TODO: could also use .rank to get a list of likelihoods
    except KeyError:
        return None
    if rank < 0.5:
        return None
    if not is_iso639_1(id1):
        log.warning(f"\t-> WARNING: detected an unknown language: {id1}")
        return None
    log.debug(f"\t-> detected language: {id1}/{lang_name(id1)}")
    return id1
