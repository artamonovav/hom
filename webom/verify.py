from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from .blocks import CJK_RE
from .config import Paths, Site
from .crawl import load_manifest

log = logging.getLogger(__name__)

ALLOWED_JP = "Открыть оригинал (日本語)"
ROUTE_RE = re.compile(r"^(/ru)?(/ownersmanual/webom/jpn/([^/]+)/)(.*)$")
YEAR_RE = re.compile(r"^(\d{4})(?:/|$)")
POINT_RE = re.compile(r'"caption"\s*:\s*"((?:\\.|[^"\\])*)"')


def _path_exists(site_dir: Path, url_path: str) -> bool:
    path = unquote(urlparse(url_path).path)
    candidates = [path]
    if path.startswith("/ru/"):
        candidates.append(path[3:])
    m = ROUTE_RE.match(path)
    if m:
        ru, prefix, car, rest = m.groups()
        bases = [prefix]
        if ru:
            bases.append(prefix[3:])
        else:
            bases.append("/ru" + prefix)
        if not YEAR_RE.match(rest):
            car_dir = site_dir / prefix.lstrip("/") / car
            years = sorted(
                (p.name for p in car_dir.iterdir() if p.is_dir() and p.name.isdigit()),
                reverse=True,
            ) if car_dir.is_dir() else []
            for base in bases:
                for year in years:
                    candidates.append(base + year + "/" + rest.lstrip("/"))
    for candidate in candidates:
        if candidate.endswith("/"):
            candidate += "index.html"
        if (site_dir / candidate.lstrip("/")).is_file():
            return True
    return False


def _check_html(path: Path, site_dir: Path, errors: list[str], warnings: list[str]) -> int:
    rel = path.relative_to(site_dir).as_posix()
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")

    for tag in soup.find_all(["script", "style", "noscript", "template", "meta"]):
        tag.decompose()
    text = soup.get_text(" ").replace(ALLOWED_JP, "")
    if CJK_RE.search(text):
        errors.append(f"{rel}: японский текст на странице")
    for tag in soup.find_all(True):
        for attr in ("alt", "title", "placeholder"):
            value = tag.get(attr)
            if value and CJK_RE.search(value):
                warnings.append(f"{rel}: японский атрибут {attr}={value[:60]!r}")

    refs: set[str] = set()
    for tag in soup.find_all(["img", "script", "link", "source", "video", "audio", "embed", "object", "input"]):
        for attr in ("src", "href", "data", "poster"):
            value = tag.get(attr)
            if value:
                refs.add(value)
        srcset = tag.get("srcset")
        if srcset:
            for part in srcset.split(","):
                if part.strip():
                    refs.add(part.strip().split()[0])
    for tag in soup.find_all(style=True):
        for m in re.finditer(r"url\(\s*['\"]?(.*?)['\"]?\s*\)", tag["style"]):
            refs.add(m.group(1))
    for tag in soup.find_all("style"):
        for m in re.finditer(r"url\(\s*['\"]?(.*?)['\"]?\s*\)", tag.get_text()):
            refs.add(m.group(1))

    page_url = "http://local/" + rel
    checked = 0
    for ref in refs:
        ref = ref.strip()
        if not ref or ref.startswith(("data:", "javascript:", "mailto:", "#")):
            continue
        absolute = urljoin(page_url, ref)
        parsed = urlparse(absolute)
        if parsed.scheme in ("http", "https") and parsed.netloc not in ("local", "www.honda.co.jp"):
            continue
        if parsed.scheme in ("http", "https") and parsed.netloc == "www.honda.co.jp":
            continue
        if not parsed.path.startswith("/"):
            continue
        checked += 1
        if not _path_exists(site_dir, parsed.path):
            errors.append(f"{rel}: битая ссылка {parsed.path}")
    return checked


def _walk_json(value, callback):
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str):
                callback(key, item)
            else:
                _walk_json(item, callback)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                callback(None, item)
            else:
                _walk_json(item, callback)


def _check_data(site_dir: Path, errors: list[str]) -> None:
    for path in sorted((site_dir / "ru").rglob("*.json")):
        rel = path.relative_to(site_dir).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            errors.append(f"{rel}: невалидный JSON")
            continue

        def check(key, value):
            if CJK_RE.search(value):
                errors.append(f"{rel}: японское значение {value[:60]!r}")

        _walk_json(data, check)

    for path in sorted((site_dir / "ru").rglob("*.point.js")):
        rel = path.relative_to(site_dir).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in POINT_RE.finditer(text):
            try:
                value = json.loads('"' + m.group(1) + '"')
            except ValueError:
                value = m.group(1)
            if CJK_RE.search(value):
                errors.append(f"{rel}: японская подпись {value[:60]!r}")


def verify_site(paths: Paths, car: str | None = None) -> dict:
    site_dir = paths.site
    errors: list[str] = []
    warnings: list[str] = []
    pages = sorted((site_dir / "ru").rglob("*.html"))
    refs = 0
    for page in pages:
        refs += _check_html(page, site_dir, errors, warnings)
    _check_data(site_dir, errors)

    # Page count per manifest, when the data directory is available.
    manifest_counts: dict[str, tuple[int, int]] = {}
    for manifest_file in sorted(paths.manifests.glob("*.json")):
        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        site_data = data.get("site", {})
        c = site_data.get("car")
        y = site_data.get("year")
        if not c or not y or (car and c != car):
            continue
        expected = len([p for p in data.get("pages", []) if p.get("status") != "error"])
        actual = len(list((site_dir / "ru" / "ownersmanual" / "webom" / "jpn" / c / y).rglob("*.html")))
        manifest_counts[f"{c}-{y}"] = (actual, expected)
        if actual != expected:
            errors.append(f"{c}-{y}: страниц {actual}, ожидалось {expected}")

    result = {
        "pages": len(pages),
        "refs": refs,
        "errors": errors,
        "warnings": warnings,
        "manifests": manifest_counts,
    }
    return result


def print_result(result: dict) -> int:
    print(f"Страниц проверено : {result['pages']}")
    print(f"Ссылок проверено  : {result['refs']}")
    print(f"Ошибок            : {len(result['errors'])}")
    for item in result["errors"][:100]:
        print("  ERROR", item)
    print(f"Предупреждений    : {len(result['warnings'])}")
    for item in result["warnings"][:40]:
        print("  WARN ", item)
    return 1 if result["errors"] else 0
