from pathlib import Path

from subsys.language_detection import langid2tesseract

try:
    from PIL import Image
except ImportError:
    import Image
import numpy as np
import pytesseract as pta

from .logger import log

# Config
pta.pytesseract.tesseract_cmd = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe").as_posix()
# TODO: put in general config, OR add script that adds checker (file exists on that os)


def tesseract_language_query(lang_ids: list[str]) -> list[str]:
    ids_new: list[str] = []
    langs_pta = pta.get_languages()
    for lang_id in lang_ids:
        language = langid2tesseract(lang_id)
        if language in langs_pta:
            ids_new.append(lang_id)
        else:
            log.warning(
                f"Language '{language}/{lang_id}' is currently not supported/installed, "
                f"choose one of {langs_pta}"
            )
    return ids_new


def ocr_pdf(data_inp: Path | np.ndarray, pdf_path_output: Path, lang_ids: str | list[str]) -> bool:
    """Create a searchable PDF.

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param pdf_path_output: full or relative path (Path-Obj or string)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: True if extraction worked, False otherwise
    """
    lang_ids = langid2tesseract(lang_ids)
    try:
        if isinstance(data_inp, Path) and data_inp.exists() and data_inp.is_file():
            pdf = pta.image_to_pdf_or_hocr(Image.open(data_inp), extension="pdf", lang=lang_ids)
        else:
            pdf = pta.image_to_pdf_or_hocr(data_inp, extension="pdf", lang=lang_ids)
    except pta.TesseractError:
        return False
    with pdf_path_output.open("w+b") as f:
        f.write(pdf)
    return True


def ocr_osd(data_inp: Path | np.ndarray, lang_ids: str | list[str]) -> str | None:
    """Get statistics about the detected text.

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: string with statistics
    """
    lang_ids = langid2tesseract(lang_ids)
    try:
        if isinstance(data_inp, Path) and data_inp.exists() and data_inp.is_file():
            text = pta.image_to_osd(Image.open(data_inp), lang=lang_ids)
        else:
            text = pta.image_to_osd(data_inp, lang=lang_ids)
    except pta.TesseractError:
        return None
    return text


def ocr_text(data_inp: Path | np.ndarray, lang_ids: str | list[str]) -> str | None:
    """Extract plain text as string.

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: string with detected text
    """
    lang_ids = langid2tesseract(lang_ids)
    try:
        if isinstance(data_inp, Path) and data_inp.exists() and data_inp.is_file():
            text = pta.image_to_string(Image.open(data_inp), lang=lang_ids)
        else:
            text = pta.image_to_string(data_inp, lang=lang_ids)
    except pta.TesseractError:
        return None
    return text
