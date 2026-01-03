from datetime import date

from dateparser.search import search_dates

# dateparser should only take full
dateparser_settings = {
    "STRICT_PARSING": True,
    "REQUIRE_PARTS": ["day", "month", "year"],
    "PREFER_LOCALE_DATE_ORDER": True,
    "PARSERS": ["custom-formats", "absolute-time"],  # custom-formats, timestamp
}

date_year_limits = [1971, date.today().year]  # lower and upper threshold


def extract_date(text: str, lang_id: str) -> str | None:
    text_dates = search_dates(
        text,
        settings=dateparser_settings,
        languages=[lang_id],
        add_detected_language=True,
    )

    # limit dates and sort from newest to oldest
    if text_dates:
        text_datetimes = [x[1] for x in text_dates]
        # TODO: further limit / filter dates for plausibility - e.g. span of last 5 +- 5 years
        # TODO: trouble with switched month / day on timestamps with day < 13, e.g. 02.12.2020
        text_datetimes = [x for x in text_datetimes if x.year >= date_year_limits[0]]
        text_datetimes = [x for x in text_datetimes if x.year <= date_year_limits[1]]
        text_datetimes = sorted(text_datetimes, key=lambda p: p.timestamp(), reverse=True)
        if text_datetimes:
            return text_datetimes[0].strftime("%Y-%m-%d")
    return None
