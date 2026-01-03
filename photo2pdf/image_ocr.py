import platform
from pathlib import Path
from warnings import deprecated

import iso639
import pytesseract as pta
from PIL import Image
from PIL.ImageFile import ImageFile

from .logger import log

try:
    pta.get_languages()
except pta.TesseractNotFoundError as xpt:
    log.debug("Tesseract is not in your PATH -> will try to use hardcoded path")
    if platform.system().lower() == "windows":
        path_ta = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if not path_ta.exists():
            msg = f"Tesseract not installed in hardcoded path {path_ta}"
            raise FileNotFoundError(msg) from xpt
        pta.pytesseract.tesseract_cmd = path_ta.as_posix()
# TODO: put in general config, OR add script that adds checker (file exists on that os)


class OCRLanguages:
    def __init__(self, id1_default: str = "en") -> None:
        self.id2s: set[str] = self._tesseract_lang_ids()
        self.id1_to_id2: dict[str, str] = {}
        for id2 in self.id2s:
            try:
                lang = iso639.Language.match(id2, strict_case=False)
            except iso639.LanguageNotFoundError:
                continue
            if lang.part1 is not None:
                self.id1_to_id2[lang.part1] = id2
        if id1_default not in self.id1_to_id2:
            raise ValueError(
                "Chosen default language (ISO 639-1:2002) is not supported by Tesseract"
            )
        self.id1_default = id1_default  # TODO: defaults not used ATM
        self.id2_default = self.id1_to_id2.get(id1_default)

    @staticmethod
    def _tesseract_lang_ids() -> set[str]:
        """Query available tesseract languages (ISO 639-2:1998 Format).

        Format is similar to 639-3:2007, but the subtypes are missing in tesseract.
        Tesseract has additional string-info like "deu_latf" (which has to be filtered).
        """
        return {_id[:3] for _id in pta.get_languages()}

    def print(self) -> None:
        log.info("Available languages in Tesseract (ISO 639-1, -2 and language name):")
        for lang_id2 in sorted(self.id2s):
            try:
                lang = iso639.Language.match(lang_id2, strict_case=False)
            except iso639.LanguageNotFoundError:
                continue
            log.info("\t%s %s %s", lang.part1 or "  ", lang_id2, lang.name)

    def query(self, lang_id1: str | None) -> str | None:
        if lang_id1 is None:
            return None
        if lang_id1 not in self.id1_to_id2:
            log.warning(f"Language '{lang_id1}' is not installed for tesseract")
            return None
        return self.id1_to_id2.get(lang_id1)

    def langid1_to_tesseract(self, lang_id1s: str | list[str]) -> str | None:
        langs = lang_id1s
        if isinstance(langs, str):
            langs = [langs]
        if isinstance(langs, list):
            langs = [self.id1_to_id2[lang] for lang in langs if lang in self.id1_to_id2]
        else:
            raise ValueError("Input of Fn not supported")
        if len(langs) < 1:
            log.warning(
                f"\t-> WARNING: unsupported languages detected ({lang_id1s}), will enable all"
            )
            return None
        return "+".join(langs)


class ImageOCR:
    """OCR class to extract text from image."""

    def __init__(self, image_path: Path, lang_id1_default: str = "en") -> None:
        if not isinstance(image_path, Path):
            raise TypeError("Provide a Path object")
        if not image_path.exists() or not image_path.is_file():
            raise ValueError("Provide a valid image path")
        self.path = image_path
        self.lang_id1_default = lang_id1_default  # TODO: not used ATM
        self.langs: str | None = None
        self.img: ImageFile = Image.open(image_path)
        # NOTE: just providing a path to tesseract saves RAM but is slower
        self.text: str = self._ocr_text(self.img, langs=self.langs)

    @staticmethod
    def _ocr_text(image: ImageFile, langs: str | None = None) -> str:
        try:
            return pta.image_to_string(image, lang=langs)
        except pta.TesseractError:
            return ""

    def get_content(self) -> str:
        if self.text is not None:
            return self.text
        return ""

    def set_language(self, lang_id2: str) -> None:
        """Set language and rerun OCR."""
        self.langs = lang_id2
        self.text = self._ocr_text(self.img, self.langs)

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
