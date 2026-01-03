from pathlib import Path
from warnings import deprecated

import numpy as np
import pytesseract as pta
from PIL import Image
from PIL.ImageFile import ImageFile

from subsys.language_detection import detect_lang
from subsys.language_detection import langid2tesseract
from subsys.language_detection import langid2tesseract_dict

from .logger import log

# Config
pta.pytesseract.tesseract_cmd = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe").as_posix()
# TODO: put in general config, OR add script that adds checker (file exists on that os)


def tesseract_languages() -> list[str]:
    return pta.get_languages()


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


@deprecated("use class")
def ocr_pdf(data_inp: Path | np.ndarray, pdf_path_output: Path, lang_ids: str | list[str]) -> bool:
    """Create a searchable PDF.

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param pdf_path_output: full or relative path (Path-Obj or string)
    :param lang_ids: short-name in tesseract format, like "deu" or "eng+fra"
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


@deprecated("use class")
def ocr_osd(data_inp: Path | np.ndarray, lang_ids: str | list[str]) -> str | None:
    """Get statistics about the detected text.

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param lang_ids: short-name in tesseract format, like "deu" or "eng+fra"
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


@deprecated("use class")
def ocr_text(data_inp: Path | np.ndarray, lang_ids: str | list[str]) -> str | None:
    """Extract plain text as string.

    :param data_inp: full or relative path (Path-Obj or string) OR raw image data (numpy ndarray)
    :param lang_ids: short-name in tesseract format, like "deu" or "eng+fra"
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


class ImageOCR:
    """OCR class to extract text from image."""

    def __init__(self, image_path: Path) -> None:
        if not isinstance(image_path, Path):
            raise TypeError("Provide a Path object")
        if not image_path.exists() or not image_path.is_file():
            raise ValueError("Provide a valid image path")
        self.path = image_path
        self.lang_ids = list(langid2tesseract_dict.keys())
        self.langs: str = langid2tesseract(self.lang_ids)
        self.img: ImageFile = Image.open(image_path)
        # NOTE: just providing a path to tesseract saves RAM but is slower
        self.angle: int = 0
        self.text: str = self._ocr_text(self.img, langs=self.langs)

    @deprecated("tesseract rotates on its own")
    def optimize_angle(self) -> int:
        angles = [0, 90, 180, 270]
        fav = (self.angle, self.text)
        for angle in angles:
            if angle == fav[0]:
                continue
            rimg = self.img.rotate(angle, expand=True)
            rtext = self._ocr_text(rimg, langs=self.langs)
            lang_id = detect_lang(rtext)
            if lang_id is not None and len(rtext) > 1.1 * len(fav[1]):
                fav = (angle, rtext)
        if fav[0] != self.angle:
            log.debug(f"corrected angle to {fav[0]} - {len(self.text)} vs {len(fav[1])} words")
            self.angle = fav[0]
            self.text = fav[1]
            self.img = self.img.rotate(fav[0], expand=True)
        return self.angle

    @staticmethod
    def _ocr_text(image: ImageFile, langs: str) -> str:
        try:
            return pta.image_to_string(image, lang=langs)
        except pta.TesseractError:
            return ""

    def get_content(self) -> str:
        if self.text is not None:
            return self.text
        return ""

    def detect_lang_id(self) -> str | None:
        """Detect language and rerun OCR."""
        lang_id = None
        if self.text is not None:
            lang_id = detect_lang(self.text)
        if lang_id is not None:
            self.lang_ids = lang_id
            self.langs = langid2tesseract(self.lang_ids)
            self.text = self._ocr_text(self.img, self.langs)
        return lang_id

    def save_pdf(self, path_output: Path | None = None) -> bool:
        """Create a searchable PDF.

        :return: True if extraction worked, False otherwise
        """
        if path_output is None:
            path_output = self.path.with_suffix(".txt")
        if path_output.exists():
            log.debug(f"File exists, won't overwrite ({path_output})")
            return None
        try:
            pdf = pta.image_to_pdf_or_hocr(self.img, extension="pdf", lang=self.langs)
        except pta.TesseractError:
            return False
        with path_output.open("w+b") as f:
            f.write(pdf)
        return True

    def save_content(self, path_output: Path | None = None) -> None:
        if path_output is None:
            path_output = self.path.with_suffix(".txt")
        if path_output.exists():
            log.debug(f"File exists, won't overwrite ({path_output})")
            return
        with path_output.open("w", encoding="utf-8-sig") as txt:
            txt.write(self.text)

    @deprecated("not needed anymore")
    def load_content(self, path_input: Path | None = None) -> str:
        if path_input is None:
            path_input = self.path.with_suffix(".txt")
        with path_input.open(encoding="utf-8-sig") as txt:
            contents = txt.readlines()
            return "\n".join(contents)

    def get_osd(self) -> str | None:
        """Get statistics about the detected text.

        :return: string with statistics
        """
        try:
            return pta.image_to_osd(self.img, lang=self.langs)
        except pta.TesseractError:
            return None
