from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .config import Paths, Site, year_dir
from .net import Fetcher
from .urls import is_page_url, is_skippable, normalize, resolve, safe_relpath, url_path

log = logging.getLogger(__name__)


def manifest_path(paths: Paths, site: Site) -> Path:
    return paths.manifests / f"{site.car}-{site.year}.json"


def load_manifest(paths: Paths, site: Site) -> dict:
    p = manifest_path(paths, site)
    if not p.exists():
        raise SystemExit(f"Манифест не найден: {p}. Сначала выполните crawl.")
    return json.loads(p.read_text(encoding="utf-8"))


def collect_links(html: str, page_url: str) -> tuple[set[str], set[str]]:
    """Return (page_urls, file_urls) found in the document."""
    soup = BeautifulSoup(html, "lxml")
    pages: set[str] = set()
    files: set[str] = set()
    for tag in soup.find_all(["a", "area"], href=True):
        href = tag["href"].strip()
        if is_skippable(href):
            continue
        absolute = resolve(page_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != "www.honda.co.jp":
            continue
        if is_page_url(absolute):
            pages.add(absolute)
        else:
            files.add(absolute)
    return pages, files


JSON_REF_RE = re.compile(r"""["']([^"'<>]+?\.json)["']""")


def _json_strings(value):
    """Yield every string nested in a JSON structure."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _json_strings(item)


def discover_json_pages(site: Site, fetcher: Fetcher,
                        raw_dir: Path | None = None) -> tuple[set[str], set[str]]:
    """Find content pages referenced from JSON databases (new-style manuals).

    Since 2023 the FREED manuals generate their side menu in JavaScript from
    ``language/ja_JP/main/json/contentsDB.json``; the HTML pages themselves are
    not linked statically.  Scan the scripts of the year's index page for JSON
    references, then turn every ``HTMLtemplate`` entry into the corresponding
    ``details/<name>.html`` (or ``detailsnavi/<name>.html``) URL.

    Returns the discovered page URLs and the relative paths of downloaded JSON
    databases (stored in ``raw_dir`` so the build can ship them).
    """
    index_url = site.root_url
    try:
        html = fetcher.get(index_url)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s: не удалось прочитать индекс для JSON-обхода: %s", site.year, exc)
        return set(), set()

    soup = BeautifulSoup(html, "lxml")
    scripts = []
    for tag in soup.find_all("script", src=True):
        url = resolve(index_url, tag["src"])
        if site.in_scope(url) and urlparse(url).path.endswith(".js"):
            scripts.append(url)

    json_urls: set[str] = set()
    for js_url in scripts:
        try:
            source = fetcher.get(js_url)
        except Exception:  # noqa: BLE001
            continue
        for ref in JSON_REF_RE.findall(source):
            url = resolve(js_url, ref)
            if site.in_scope(url):
                json_urls.add(url)

    pages: set[str] = set()
    data_files: set[str] = set()
    for json_url in sorted(json_urls):
        try:
            text = fetcher.get(json_url)
            data = json.loads(text.lstrip("\ufeff"))
        except Exception:  # noqa: BLE001
            continue
        if raw_dir is not None:
            rel = json_url[len(site.root_url):].split("?", 1)[0]
            dest = raw_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text.lstrip("\ufeff"), encoding="utf-8")
            data_files.add(rel)
        subdir = "detailsnavi" if "/navi/" in json_url else "details"
        for value in _json_strings(data):
            name = value.rsplit("/", 1)[-1]
            if name.endswith(".html"):
                pages.add(urljoin(site.root_url, f"{subdir}/{name}"))
    if pages:
        log.info("JSON-обход: %d страниц из %d баз", len(pages), len(json_urls))
    return pages, data_files


def crawl(site: Site, paths: Paths, fetcher: Fetcher | None = None,
          max_pages: int | None = None, force: bool = False) -> dict:
    fetcher = fetcher or Fetcher()
    raw_dir = year_dir(paths, site, "raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    queue: deque[str] = deque([site.root_url])
    queued = {site.root_url}

    # The agreement text is not linked from the manual navigation; it is
    # loaded by an AJAX call from common.js / library.js.  Save it as a normal
    # page so the offline copy (and the Russian translation) contains it.
    agreement_url = urljoin(site.root_url, "agreement.html")
    if site.in_scope(agreement_url):
        queued.add(agreement_url)
        queue.append(agreement_url)

    extra_pages, data_files = discover_json_pages(site, fetcher, raw_dir)
    for extra in sorted(extra_pages):
        if site.in_scope(extra) and extra not in queued:
            queued.add(extra)
            queue.append(extra)
    pages: dict[str, dict] = {}
    file_links: set[str] = set()
    started = time.time()

    while queue:
        url = queue.popleft()
        if max_pages and len(pages) >= max_pages:
            break
        rel = site.rel_path(url)
        dest = raw_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        html: str | None = None
        status = "cached"
        if dest.exists() and dest.stat().st_size > 0 and not force:
            html = dest.read_text(encoding="utf-8", errors="replace")
        if html is None:
            status = "fetched"
            try:
                html = fetcher.get(url)
            except Exception as exc:  # noqa: BLE001
                log.error("FAIL %s: %s", url, exc)
                pages[url] = {"url": url, "path": rel, "status": "error", "error": str(exc)}
                continue
            dest.write_text(html, encoding="utf-8")

        soup = BeautifulSoup(html, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else ""
        pages[url] = {
            "url": url,
            "path": rel,
            "title": title,
            "status": status,
            "bytes": len(html.encode("utf-8")),
            "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        }

        found_pages, found_files = collect_links(html, url)
        file_links |= found_files
        for link in sorted(found_pages):
            if site.in_scope(link) and link not in queued:
                queued.add(link)
                queue.append(link)

        n = len(pages)
        if n % 10 == 0 or n == 1:
            log.info("страниц: %d, в очереди: %d | %s", n, len(queue), url)

    manifest = {
        "site": {"car": site.car, "year": site.year, "base": site.base,
                 "root_url": site.root_url},
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_sec": round(time.time() - started, 1),
        "pages": sorted(pages.values(), key=lambda p: p["path"]),
        "file_links": sorted(file_links),
        "data_files": sorted(data_files),
    }
    mp = manifest_path(paths, site)
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("готово: %d страниц, %d файловых ссылок -> %s",
             len(pages), len(file_links), mp)
    return manifest


def discover_years(site: Site, fetcher: Fetcher | None = None) -> list[str]:
    fetcher = fetcher or Fetcher()
    url = site.year_index_url
    html = fetcher.get(url)
    soup = BeautifulSoup(html, "lxml")
    years: set[str] = set()
    for a in soup.find_all("a", href=True):
        absolute = resolve(url, a["href"])
        if not absolute.startswith(url):
            continue
        rel = absolute[len(url):].strip("/")
        if len(rel) == 4 and rel.isdigit():
            years.add(rel)
    return sorted(years, reverse=True)
