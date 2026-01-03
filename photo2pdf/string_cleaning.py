"""Collection of Functions to clean up strings."""

from pathlib import Path

replacements: dict[str, str] = {
    # newlines
    "\n": "",
    "\r": "",
    # punctuation
    ".": " ",
    "!": " ",
    "?": " ",
    ",": " ",
    # special characters
    "\t": " ",  # TAB
    " ": " ",  # noqa: RUF001, a special space, looks the same..
    "   ": " ",  # 3 spaces
    "  ": " ",  # 2 spaces
}


def str_filter(item: str) -> str:
    """Cleanup strings by removing unwanted characters."""
    item = item.lower()
    for key, value in replacements.items():
        item = item.replace(key, value)
    return item


def import_list(file: Path) -> list[str]:
    """Load textfile with lines as list of strings."""
    # TODO: not correct location for this fn
    with file.open(encoding="utf-8-sig") as logfile:
        data = logfile.readlines()

    data = [date[0 : date.find("#")] for date in data]  # filter comments, from # anywhere to EOL
    data = [str_filter(date) for date in data]
    data = [date.strip() for date in data]  # remove whitespace from beginning and end
    return [date for date in data if len(date) > 0]
