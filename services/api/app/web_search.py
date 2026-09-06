from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


class WebSearch:
    """Small provider-neutral search boundary.

    DuckDuckGo HTML is used as a development provider; production search
    providers can be added without changing the agent/tool contract.
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        query = query.strip()
        if not query:
            raise ValueError("search query must not be empty")
        limit = max(1, min(limit, 10))
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        response = httpx.get(url, headers={"User-Agent": "AETHON-Web/0.1"}, timeout=self.timeout)
        response.raise_for_status()
        # Keep parsing intentionally isolated; a structured search-provider
        # adapter can replace this implementation without changing callers.
        from html.parser import HTMLParser

        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.items: list[SearchResult] = []
                self.href = None
                self.title = []
                self.snippet = []
                self.in_result = False
                self.in_snippet = False

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and "result__a" in attrs.get("class", ""):
                    self.in_result = True
                    self.href = attrs.get("href")
                    self.title = []
                elif tag in {"a", "div"} and "result__snippet" in attrs.get("class", ""):
                    self.in_snippet = True
                    self.snippet = []

            def handle_endtag(self, tag):
                if tag == "a" and self.in_result:
                    if self.href and self.title:
                        self.items.append(SearchResult("".join(self.title).strip(), self.href, "", "duckduckgo"))
                    self.in_result = False
                elif tag == "div" and self.in_snippet:
                    if self.items:
                        self.items[-1] = SearchResult(self.items[-1].title, self.items[-1].url, "".join(self.snippet).strip(), "duckduckgo")
                    self.in_snippet = False

            def handle_data(self, data):
                if self.in_result:
                    self.title.append(data)
                if self.in_snippet:
                    self.snippet.append(data)

        parser = Parser()
        parser.feed(response.text)
        return parser.items[:limit]
