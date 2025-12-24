from pathlib import Path

try:
    from PIL import Image
except ImportError:
    import Image

import numpy as np
import pytesseract as pta


def ocr_pdf(data_inp: Path | np.ndarray, pdf_path_output: Path, language: str = "eng") -> bool:
    """Create a searchable PDF

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param pdf_path_output: full or relative path (Path-Obj or string)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: True if extraction worked, False otherwise
    """
    try:
        pdf = pta.image_to_pdf_or_hocr(data_inp, extension="pdf", lang=language)
    except pta.TesseractError:
        return False
    with pdf_path_output.open("w+b") as f:
        f.write(pdf)
    return True


def ocr_osd(data_inp: Path | np.ndarray, language: str = "eng") -> str:
    """Get statistics about the detected text

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: string with statistics
    """
    try:
        if isinstance(data_inp, Path) and data_inp.exists() and data_inp.is_file():
            text = pta.image_to_osd(Image.open(data_inp), lang=language)
        elif isinstance(data_inp, np.ndarray):
            text = pta.image_to_osd(data_inp, lang=language)
        else:
            text = ""
    except pta.TesseractError:
        text = ""
    return text


def ocr_text(data_inp: Path | np.ndarray, language: str = "") -> str:
    """Extracts plain text as string

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: string with detected text
    """
    try:
        if isinstance(data_inp, Path) and data_inp.exists() and data_inp.is_file():
            text = pta.image_to_string(Image.open(data_inp), lang=language)
        elif isinstance(data_inp, np.ndarray):
            text = pta.image_to_string(data_inp, lang=language)
        else:
            text = ""
    except pta.TesseractError:
        text = ""
    return text
