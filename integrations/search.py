from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Sucht im Internet via DuckDuckGo — kostenlos, kein API Key."""
    try:
        results = DDGS().text(query, region="de-de", max_results=max_results)
        return [{"title": r["title"], "body": r["body"], "url": r["href"]} for r in results]
    except Exception as e:
        return [{"error": str(e)}]


def search_news(query: str, max_results: int = 5) -> list[dict]:
    """Sucht aktuelle News via DuckDuckGo."""
    try:
        results = DDGS().news(query, region="de-de", max_results=max_results)
        return [{"title": r["title"], "body": r["body"], "date": r.get("date", ""), "url": r["url"]} for r in results]
    except Exception as e:
        return [{"error": str(e)}]
