from pathlib import Path
from warnings import deprecated

import pytesseract as pta
from PIL import Image
from PIL.ImageFile import ImageFile

from .language_detection import detect_lang
from .language_detection import langid2tesseract
from .language_detection import langid2tesseract_dict
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
            return False
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
