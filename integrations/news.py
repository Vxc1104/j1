import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime

RSS_FEEDS = {
    "welt": "https://www.welt.de/feeds/topnews.rss",
    "spiegel": "https://www.spiegel.de/schlagzeilen/tops/index.rss",
    "tagesschau": "https://www.tagesschau.de/xml/rss2/",
    "business": "https://www.handelsblatt.com/contentexport/feed/top-themen",
    "tech": "https://feeds.feedburner.com/techcrunch",
    "finanzen": "https://www.finanzen.net/rss/news",
}


def get_news(topic: str = "welt", max_results: int = 5) -> list[dict]:
    feed_url = RSS_FEEDS.get(topic.lower(), RSS_FEEDS["tagesschau"])
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:max_results]:
            published = ""
            if hasattr(entry, "published"):
                published = entry.published
            articles.append({
                "title": entry.get("title", ""),
                "summary": _clean(entry.get("summary", entry.get("description", ""))),
                "published": published,
                "link": entry.get("link", ""),
            })
        return articles
    except Exception as e:
        return [{"error": str(e)}]


def get_top_news(max_results: int = 5) -> list[dict]:
    return get_news("tagesschau", max_results)


def _clean(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ").strip()
        return text[:300] if len(text) > 300 else text
    except Exception:
        return html[:300] if len(html) > 300 else html
