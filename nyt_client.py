import requests
from dataclasses import dataclass
from typing import Optional


@dataclass
class Article:
    title: str
    abstract: str
    byline: str
    section: str
    published_date: str
    url: str


def fetch_top_stories(api_key: str, section: str = "home") -> list[Article]:
    url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json"
    resp = requests.get(url, params={"api-key": api_key}, timeout=15)
    resp.raise_for_status()

    articles = []
    for item in resp.json().get("results", []):
        articles.append(Article(
            title=item.get("title", ""),
            abstract=item.get("abstract", ""),
            byline=item.get("byline", ""),
            section=item.get("section", ""),
            published_date=item.get("published_date", "")[:10],
            url=item.get("url", ""),
        ))

    return articles
