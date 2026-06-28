import requests

from models import Article

API_URL = "https://content.guardianapis.com/search"


def fetch_articles(
    api_key: str,
    *,
    section: str | None = None,
    max_articles: int = 8,
) -> list[Article]:
    """Fetch full-text articles from The Guardian Open Platform.

    Unlike most free APIs, Guardian returns the complete article body
    (`fields.bodyText`) on the free tier — so every article is full text.
    """
    params = {
        "api-key": api_key,
        "order-by": "newest",
        "page-size": max_articles,
        "show-fields": "bodyText,byline,trailText",
    }
    if section:
        params["section"] = section

    resp = requests.get(API_URL, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json().get("response", {})

    if payload.get("status") != "ok":
        raise RuntimeError(f"Guardian API error: {payload}")

    articles: list[Article] = []
    for item in payload.get("results", []):
        fields = item.get("fields", {})
        body = fields.get("bodyText") or fields.get("trailText") or ""
        if not body.strip():
            continue
        articles.append(Article(
            title=item.get("webTitle", ""),
            body=body,
            byline=fields.get("byline", ""),
            section=item.get("sectionName", ""),
            published_date=(item.get("webPublicationDate", "") or "")[:10],
            url=item.get("webUrl", ""),
            is_full=bool(fields.get("bodyText")),
            source="The Guardian",
        ))

    return articles
