"""Public EA headlines only; never fetches authenticated club or arbitrary URLs."""
from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import httpx

BUILTIN = json.loads((Path(__file__).resolve().parent.parent / "data" / "fc27_content.json").read_text())
NEWS_SOURCES = {"FC27": "https://www.ea.com/games/ea-sports-fc/fc-27"}
MAX_NEWS_BYTES = 2_000_000

class NewsLinks(HTMLParser):
    def __init__(self, version):
        super().__init__()
        self.version = version
        self.links = []
        self.href = None
        self.parts = []
        self.label = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attributes = dict(attrs)
            self.href = (attributes.get("href") or "").strip()
            self.label = attributes.get("aria-label") or attributes.get("title")
            self.parts = []

    def handle_data(self, data):
        if self.href: self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != "a" or not self.href: return
        url = urljoin("https://www.ea.com", self.href)
        parsed = urlsplit(url)
        required_path = f"/games/ea-sports-fc/fc-{self.version[2:]}/news/"
        if parsed.scheme == "https" and parsed.hostname in ("www.ea.com", "ea.com") and required_path in parsed.path:
            title = " ".join((self.label or " ".join(self.parts)).split())[:220]
            if not title or title.casefold() in {"learn more", "read more", "más información", "ver más"}:
                title = parsed.path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").strip().capitalize()[:220]
            self.links.append({"title": title, "url": parsed._replace(query="", fragment="").geturl(), "published_at": None})
        self.href = None
        self.parts = []


def builtin_content(version):
    if version == "FC27":
        result = deepcopy(BUILTIN)
        result['articles'] = [a for a in result['articles'] if active_article(a)]
        if not active_evidence(result):
            result.update(features=[], verified_at=None)
        return result
    return {"game_version": version, "verified_at": None, "features": [], "articles": [], "scoring": None}


def active_evidence(item):
    try:
        observed = datetime.fromisoformat(item['observed_at'])
        until = datetime.fromisoformat(item['valid_until'])
        return (item.get('game_version') == 'FC27' and item.get('validation_status') == 'documented'
                and observed <= datetime.now(timezone.utc) < until)
    except (KeyError, TypeError, ValueError):
        return False


def active_article(item):
    if not isinstance(item, dict) or not active_evidence(item):
        return False
    try:
        url = urlsplit(item['url'])
        published = datetime.fromisoformat(item['published_at']).date()
        return (url.scheme == 'https' and url.hostname in {'ea.com', 'www.ea.com'}
                and not url.username and not url.password and not url.query and not url.fragment
                and url.path.startswith('/games/ea-sports-fc/fc-27/news/')
                and published <= datetime.fromisoformat(item['observed_at']).date())
    except (KeyError, TypeError, ValueError):
        return False


def fetch_news(version):
    url = NEWS_SOURCES.get(version)
    if not url: raise ValueError("Todavía no hay una fuente pública configurada para esta edición.")
    data = bytearray()
    # No redirects, URL input, credentials or account cookies can enter this path.
    # Respect the installation's outbound proxy; the destination remains fixed.
    with httpx.Client(timeout=httpx.Timeout(15, connect=5), follow_redirects=False) as client:
        with client.stream("GET", url, headers={"Accept": "text/html", "User-Agent": "ClubLab/2.0 (public news reader)"}) as response:
            response.raise_for_status()
            if "text/html" not in response.headers.get("content-type", "").lower():
                raise ValueError("La fuente no devolvió una página HTML.")
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > MAX_NEWS_BYTES: raise ValueError("La página supera el límite de lectura.")
    parser = NewsLinks(version)
    parser.feed(data.decode("utf-8", errors="replace"))
    seen = set()
    articles = []
    for article in parser.links:
        if article["url"] not in seen:
            articles.append(article)
            seen.add(article["url"])
    if not articles:
        raise ValueError("EA no expuso enlaces de noticias legibles. Se conserva la última lista disponible.")
    return {"articles": articles[:30], "last_checked": datetime.now(timezone.utc).isoformat(), "refresh_error": None}
