from langid.langid import LanguageIdentifier
from langid.langid import model
from stop_words import LANGUAGE_MAPPING

from .logger import log

langid2nltk_dict: dict[str, str] = {"de": "german", "en": "english"}
# TODO: output of one lib does not fit into others
#   for nltk see https://pypi.org/project/stop-words/
#   tesseract is even stranger

langid2tesseract_dict: dict[str, str] = {"de": "deu", "en": "eng"}

# ['afr', 'amh', 'ara', 'asm', 'aze', 'aze_cyrl', 'bel', 'ben', 'bod',
# 'bos', 'bre', 'bul', 'cat', 'ceb', 'ces', 'chi_sim', 'chi_sim_vert',
# 'chi_tra', 'chi_tra_vert', 'chr', 'cos', 'cym', 'dan', 'deu', 'deu_latf',
# 'div', 'dzo', 'ell', 'eng', 'enm', 'epo', 'equ', 'est', 'eus', 'fao', 'fas',
# 'fil', 'fin', 'fra', 'frm', 'fry', 'gla', 'gle', 'glg', 'grc', 'guj', 'hat',
# 'heb', 'hin', 'hrv', 'hun', 'hye', 'iku', 'ind', 'isl', 'ita', 'ita_old', 'jav',
# 'jpn', 'jpn_vert', 'kan', 'kat', 'kat_old', 'kaz', 'khm', 'kir', 'kmr', 'kor',
# 'lao', 'lat', 'lav', 'lit', 'ltz', 'mal', 'mar', 'mkd', 'mlt', 'mon', 'mri', 'msa',
# 'mya', 'nep', 'nld', 'nor', 'oci', 'ori', 'osd', 'pan', 'pol', 'por', 'pus', 'que',
# 'ron', 'rus', 'san', 'sin', 'slk', 'slv', 'snd', 'spa', 'spa_old', 'sqi', 'srp', 'srp_latn',
# 'sun', 'swa', 'swe', 'syr', 'tam', 'tat', 'tel', 'tgk', 'tha', 'tir', 'ton', 'tur', 'uig',
# 'ukr', 'urd', 'uzb', 'uzb_cyrl', 'vie', 'yid', 'yor']
# lang_id -> iso 639-1:2002
# tesseract -> iso 639-2:1998 (similar to 639-3:2007 but the subtypes are missing in tesseract)

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


def langid2tesseract(lang_ids: str | list[str] = langid2tesseract_dict.keys()) -> str:
    # TODO: this should also query available / installed lang in tesseract
    langs = lang_ids
    if isinstance(langs, str):
        langs = [langs]
    if isinstance(langs, list):
        langs = [langid2tesseract_dict[lang] for lang in langs if lang in langid2tesseract_dict]
    if len(langs) < 1:
        log.warning(f"\t-> WARNING: unsupported languages detected ({lang_ids}), will enable all")
        langs = list(langid2tesseract_dict.values())
    return "+".join(langs)
