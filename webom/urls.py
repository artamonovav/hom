from __future__ import annotations

import re
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse, unquote

SKIP_SCHEMES = ("mailto:", "javascript:", "tel:", "data:", "ftp:")


def normalize(url: str) -> str:
    """Drop fragment and query string, keep a canonical absolute URL."""
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    if not parsed.scheme:
        return url
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def is_http(url: str) -> bool:
    return urlparse(url).scheme in ("http", "https")


def is_page_url(url: str) -> bool:
    path = urlparse(url).path
    if path.endswith((".html", ".htm")):
        return True
    return path.endswith("/")


def is_skippable(href: str) -> bool:
    href = href.strip()
    if not href or href.startswith("#"):
        return True
    return href.lower().startswith(SKIP_SCHEMES)


def url_path(url: str) -> str:
    return urlparse(url).path


def safe_relpath(path: str) -> str:
    """URL path -> safe relative filesystem path (no leading slash)."""
    path = unquote(urlparse(path).path)
    parts = [p for p in path.split("/") if p not in ("", ".", "..")]
    return "/".join(parts)


def resolve(base_url: str, href: str) -> str:
    return normalize(urljoin(base_url, href))


_CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)
_CSS_IMPORT_RE = re.compile(r"@import\s+(?:url\(\s*)?(['\"])(.*?)\1", re.I | re.S)


def css_refs(css: str) -> set[str]:
    refs: set[str] = set()
    for m in _CSS_IMPORT_RE.finditer(css):
        refs.add(m.group(2))
    for m in _CSS_URL_RE.finditer(css):
        ref = m.group(2).strip()
        if ref and not ref.lower().startswith(("data:", "#")):
            refs.add(ref)
    return refs


def srcset_urls(value: str) -> list[str]:
    urls = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        urls.append(part.split()[0])
    return urls
