import requests

from models import Article

API_URL = "https://newsdata.io/api/1/latest"


def _pick_body(item: dict) -> tuple[str, bool]:
    """Prefer full content; fall back to description. Returns (text, is_full)."""
    content = item.get("content")
    placeholder = "ONLY AVAILABLE IN PAID PLANS"
    if content and placeholder not in content:
        return content, True
    return item.get("description") or "", False


def fetch_articles(
    api_key: str,
    *,
    country: str = "us",
    category: str | None = None,
    language: str = "en",
    max_articles: int = 15,
    priority_domain: str | None = "top",
    full_content: bool = False,
) -> list[Article]:
    params = {
        "apikey": api_key,
        "country": country,
        "language": language,
    }
    if category:
        params["category"] = category
    if priority_domain:
        # "top" restricts to major outlets (BBC, USA Today, ...) and filters out
        # the press-release spam that the unfiltered feed returns
        params["prioritydomain"] = priority_domain
    if full_content:
        # PAID-ONLY: free plans return 422 if this is sent
        params["full_content"] = 1

    articles: list[Article] = []
    next_page = None

    # Paginate until we have enough (each page returns ~10)
    while len(articles) < max_articles:
        if next_page:
            params["page"] = next_page

        resp = requests.get(API_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "success":
            raise RuntimeError(f"NewsData.io error: {data}")

        for item in data.get("results", []):
            body, is_full = _pick_body(item)
            if not body.strip():
                continue  # skip articles with no usable text (avoids blank pages)
            creator = item.get("creator")
            byline = ", ".join(creator) if isinstance(creator, list) else (creator or "")
            categories = item.get("category") or []
            articles.append(Article(
                title=item.get("title", ""),
                body=body,
                byline=byline,
                section=(categories[0] if categories else "").title(),
                published_date=(item.get("pubDate", "") or "")[:10],
                url=item.get("link", ""),
                is_full=is_full,
                source="NewsData.io",
            ))
            if len(articles) >= max_articles:
                break

        next_page = data.get("nextPage")
        if not next_page:
            break

    return articles[:max_articles]
