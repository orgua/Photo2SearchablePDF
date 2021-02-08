from pathlib import Path

try:
    from PIL import Image
except ImportError:
    import Image

import pytesseract as pta
import numpy as np


def ocr_pdf(data_inp, pdf_path_output: str, language: str = "eng"):
    """ create a searchable PDF

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param pdf_path_output: full or relative path (Path-Obj or string)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: True if extraction worked, False otherwise
    """
    try:
        if isinstance(data_inp, str) or isinstance(data_inp, Path) or isinstance(data_inp, np.ndarray):
            pdf = pta.image_to_pdf_or_hocr(data_inp, extension='pdf', lang=language)
        else:
            return False
    except pta.TesseractError:
        return False
    with open(pdf_path_output, 'w+b') as f:
        f.write(pdf)
    return True


def ocr_osd(data_inp, language: str = "eng"):
    """ get statistics about the detected text

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: string with statistics
    """
    try:
        if isinstance(data_inp, str) or isinstance(data_inp, Path):
            # interpret as path
            text = pta.image_to_osd(Image.open(data_inp), lang=language)
        elif isinstance(data_inp, np.ndarray):
            text = pta.image_to_osd(Image.open(data_inp), lang=language)
        else:
            text = ""
    except pta.TesseractError:
        text = ""
    return text


def ocr_text(data_inp, language: str = ""):
    """ extracts plain text as string

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param language: short-name in tesseract format, like "deu" or "eng+fra"
    :return: string with detected text
    """
    try:
        if isinstance(data_inp, str) or isinstance(data_inp, Path):
            text = pta.image_to_string(Image.open(data_inp), lang=language)
        elif isinstance(data_inp, np.ndarray):
            text = pta.image_to_string(data_inp, lang=language)
        else:
            text = ""
    except pta.TesseractError:
        text = ""
    return text
