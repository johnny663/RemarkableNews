from dataclasses import dataclass


@dataclass
class Article:
    title: str
    body: str          # full content if available, else a summary
    byline: str
    section: str
    published_date: str
    url: str
    is_full: bool      # True if full article text, False if only a summary
    source: str = ""   # e.g. "The Guardian", "NewsData.io"
