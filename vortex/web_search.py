"""
Vortex Desktop Pet — Web Search

Provides internet access via DuckDuckGo search and URL fetching.
No API keys needed.
"""

import json
import re
import html
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote_plus


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def search_web(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo and return results as text.

    Returns a formatted string with titles, URLs, and snippets.
    """
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        results = []
        # Parse the HTML results (simple regex extraction)
        # DuckDuckGo HTML has result blocks with class "result"
        blocks = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'<a class="result__snippet"[^>]*>(.*?)</a>',
            raw, re.DOTALL
        )

        for href, title, snippet in blocks[:max_results]:
            title = _strip_html(title).strip()
            snippet = _strip_html(snippet).strip()
            if title and snippet:
                results.append(f"- {title}\n  {snippet}")

        if not results:
            # Fallback: try to extract any links with text
            links = re.findall(
                r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', raw, re.DOTALL
            )
            for link_text in links[:max_results]:
                clean = _strip_html(link_text).strip()
                if clean:
                    results.append(f"- {clean}")

        return "\n".join(results) if results else "No se encontraron resultados."

    except Exception as e:
        return f"Error de búsqueda: {e}"


def fetch_url(url: str, max_chars: int = 3000) -> str:
    """Fetch a URL and return its text content (stripped of HTML).

    Returns plain text extracted from the page.
    """
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8", errors="replace")

        if "html" in content_type.lower() or raw.strip().startswith("<"):
            # Strip HTML tags and get text
            text = _strip_html(raw)
            # Collapse whitespace
            text = re.sub(r'\s+', ' ', text).strip()
        else:
            text = raw.strip()

        return text[:max_chars] if text else "No se pudo extraer contenido."

    except Exception as e:
        return f"Error al acceder a la URL: {e}"


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    return text
