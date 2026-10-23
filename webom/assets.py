from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .config import Paths, Site, year_dir
from .crawl import load_manifest
from .net import Fetcher
from .urls import css_refs, is_page_url, is_skippable, normalize, resolve, safe_relpath, srcset_urls

log = logging.getLogger(__name__)

ASSET_ATTRS = {
    "img": ("src", "data-src", "data-original"),
    "source": ("src",),
    "script": ("src",),
    "link": ("href",),
    "video": ("src", "poster"),
    "audio": ("src",),
    "embed": ("src",),
    "object": ("data",),
    "input": ("src",),
}

ALLOWED_EXT = {
    ".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".ico", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp4", ".webm",
    ".ogg", ".mp3", ".wav", ".pdf", ".zip", ".json", ".xml", ".txt",
}
SKIP_PATH_PARTS = ("/common/beacon/", "/search/")

# Assets referenced only from JavaScript / JSON are not visible to the HTML
# scanner.  This expression intentionally catches both quoted and escaped
# strings (for example ``src=\"../../img/foo.png\"`` inside a JSON value).
_CODE_REF_RE = re.compile(
    r'''(?P<url>
        (?:https?:)?//[^\s"'<>]+
        |
        (?:[A-Za-z0-9_@%+=,~./-]*?)\.(?:json|mjs|css|js|jpe?g|png|gif|svg|webp|ico|
            woff2?|ttf|otf|eot|mp4|webm|ogg|mp3|wav|pdf|zip)
        (?![A-Za-z0-9])
        (?:\?[^\s"'<>]*)?
        (?:\#[^\s"'<>]*)?
    )''',
    re.I | re.X,
)


def _same_origin(url: str) -> bool:
    p = urlparse(url)
    return p.scheme in ("http", "https") and p.netloc == "www.honda.co.jp"


def _accept(url: str) -> bool:
    if not _same_origin(url):
        return False
    path = urlparse(url).path
    if is_page_url(url):
        return False
    if any(part in path for part in SKIP_PATH_PARTS):
        return False
    ext = Path(path).suffix.lower()
    return ext in ALLOWED_EXT or ext == ""


def collect_code_refs(text: str, base_urls: set[str] | list[str]) -> set[str]:
    """Return same-origin asset URLs referenced from JS or JSON text.

    Relative references are resolved against every plausible page base.  A
    script can be included from the year root, from ``details/`` and from
    ``visual/``; trying all of them keeps the crawler conservative.  Wrong
    candidates simply 404 and are ignored.
    """
    bases = [b for b in base_urls if b] or [""]
    urls: set[str] = set()
    for match in _CODE_REF_RE.finditer(text):
        raw = match.group("url").strip().rstrip("\\,;)]")
        if not raw or raw.startswith(("data:", "javascript:", "mailto:", "#")):
            continue
        if raw.startswith("//"):
            raw = "https:" + raw
        if raw.startswith(("http://", "https://")):
            candidates = [raw]
        else:
            variants = [raw]
            # Some JSON files contain paths written for a page one level
            # deeper (for example ../../../img in visualindex_content.json,
            # which visual.js normalises with replace("../../", "")).  Try the
            # shortened form as well; a wrong candidate only costs a 404.
            if raw.startswith("../../../"):
                variants.append(raw[6:])
            elif raw.startswith("../../"):
                variants.append(raw[3:])
            candidates = [urljoin(base, variant) for variant in variants for base in bases]
        for candidate in candidates:
            try:
                candidate = normalize(candidate)
            except ValueError:
                # Broken/placeholder URLs can contain non-ASCII netlocs;
                # urlparse rejects those under NFKC normalisation.
                continue
            if _accept(candidate):
                urls.add(candidate)
    return urls


def collect_page_assets(html: str, page_url: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: set[str] = set()

    for tag_name, attrs in ASSET_ATTRS.items():
        for tag in soup.find_all(tag_name):
            for attr in attrs:
                value = tag.get(attr)
                if not value:
                    continue
                if attr == "srcset":
                    continue
                if is_skippable(value):
                    continue
                urls.add(resolve(page_url, value))

    for tag in soup.find_all(["img", "source"]):
        srcset = tag.get("srcset")
        if srcset:
            for u in srcset_urls(srcset):
                urls.add(resolve(page_url, u))

    for tag in soup.find_all(style=True):
        for ref in css_refs(tag["style"]):
            urls.add(resolve(page_url, ref))

    for tag in soup.find_all("style"):
        for ref in css_refs(tag.get_text()):
            urls.add(resolve(page_url, ref))

    for tag in soup.find_all(["body", "table", "td", "tr"]):
        bg = tag.get("background")
        if bg and not is_skippable(bg):
            urls.add(resolve(page_url, bg))

    return {u for u in urls if _accept(u)}


def asset_local_path(url: str) -> Path:
    p = urlparse(url)
    return Path(p.netloc) / safe_relpath(p.path)


def _page_script_context(html: str, page_url: str) -> tuple[set[str], set[str], set[str]]:
    """Return (external scripts, inline code refs, all code refs)."""
    soup = BeautifulSoup(html, "lxml")
    scripts: set[str] = set()
    inline_refs: set[str] = set()
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if src:
            url = resolve(page_url, src)
            if _accept(url) and urlparse(url).path.lower().endswith((".js", ".mjs")):
                scripts.add(url)
        else:
            inline_refs |= collect_code_refs(tag.get_text(), {page_url})
    return scripts, inline_refs, set()


def download_assets(site: Site, paths: Paths,
                    fetcher: Fetcher | None = None,
                    workers: int = 4) -> dict:
    fetcher = fetcher or Fetcher(min_interval=0.12)
    manifest = load_manifest(paths, site)
    raw_dir = year_dir(paths, site, "raw")
    assets_dir = paths.assets

    pending: dict[str, set[str]] = {}
    seen: set[str] = set()
    code_bases: dict[str, set[str]] = {}
    processed_code: set[str] = set()
    entries: list[dict] = []

    def is_code(url: str) -> bool:
        return Path(urlparse(url).path).suffix.lower() in (".css", ".js", ".mjs", ".json")

    def add(url: str, bases: set[str]) -> None:
        if not url or not _accept(url):
            return
        url = normalize(url)
        clean_bases = {b for b in bases if b}
        if url in seen:
            if is_code(url):
                code_bases.setdefault(url, set()).update(clean_bases)
            return
        pending.setdefault(url, set()).update(clean_bases)
        if is_code(url):
            code_bases.setdefault(url, set()).update(clean_bases)

    # File links found in anchors, plus all resources referenced by HTML.
    for url in manifest.get("file_links", []):
        add(url, {site.root_url})

    for page in manifest["pages"]:
        if page.get("status") == "error":
            continue
        html = (raw_dir / page["path"]).read_text(encoding="utf-8", errors="replace")
        page_url = page["url"]
        for url in collect_page_assets(html, page_url):
            add(url, {page_url})

        scripts, inline_refs, _ = _page_script_context(html, page_url)
        for script_url in scripts:
            add(script_url, {page_url})
            code_bases.setdefault(script_url, set()).add(page_url)
        for ref in inline_refs:
            add(ref, {page_url})

    def fetch_one(url: str) -> tuple[str, bytes | None, str | None]:
        dest = assets_dir / asset_local_path(url)
        if dest.exists() and dest.stat().st_size > 0:
            return url, None, None
        try:
            data = fetcher.get(url, binary=True)
            return url, data, None
        except Exception as exc:  # noqa: BLE001
            return url, None, str(exc)

    round_no = 0
    while pending:
        round_no += 1
        batch = sorted(pending)
        pending = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fetch_one, u): u for u in batch if u not in seen}
            for fut in as_completed(futures):
                url = futures[fut]
                seen.add(url)
                _, data, error = fut.result()
                if error:
                    # Trying several page bases produces benign 404s; keep the
                    # log useful by only warning about real failures.
                    if "404" not in error:
                        log.warning("asset FAIL %s: %s", url, error)
                    entries.append({"url": url, "status": "error", "error": error})
                    continue
                dest = assets_dir / asset_local_path(url)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if data is not None:
                    dest.write_bytes(data)
                entries.append({
                    "url": url,
                    "path": str(asset_local_path(url)),
                    "bytes": dest.stat().st_size,
                    "status": "ok",
                })
        log.info("ассеты: круг %d, проверено %d", round_no, len(seen))

        # Follow references in CSS, JS and JSON.  Code references are resolved
        # against the pages that include the script, because paths such as
        # ``../img/foo.png`` are relative to the document, not the script.
        parse_urls = [
            url for url in seen
            if url not in processed_code and is_code(url)
        ]
        for url in sorted(parse_urls):
            processed_code.add(url)
            dest = assets_dir / asset_local_path(url)
            if not dest.exists():
                continue
            try:
                text = dest.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            bases = set(code_bases.get(url, set()))
            bases.add(url)
            ext = Path(urlparse(url).path).suffix.lower()
            if ext == ".css":
                refs = {resolve(url, ref) for ref in css_refs(text)}
            else:
                refs = collect_code_refs(text, bases)
            for ref in refs:
                add(ref, bases)

    out = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "assets": sorted(entries, key=lambda e: e["url"]),
    }
    out_path = assets_dir / "manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for e in entries if e["status"] == "ok")
    log.info("ассеты готовы: %d ok -> %s", ok, out_path)
    return out


def asset_file(paths: Paths, site: Site, rel: str) -> Path:
    """Path of a downloaded asset inside data/assets (rel to year root)."""
    return paths.assets / "www.honda.co.jp" / site.root_path.strip("/") / rel


def load_assets_manifest(paths: Paths) -> dict:
    p = paths.assets / "manifest.json"
    if not p.exists():
        return {"assets": []}
    return json.loads(p.read_text(encoding="utf-8"))
