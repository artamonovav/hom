from __future__ import annotations

import json
import logging
import re
import time

from bs4 import BeautifulSoup

from .blocks import collect_html, collect_plain
from .config import Paths, Site
from .crawl import load_manifest

log = logging.getLogger(__name__)

# Boilerplate of the Honda web-manual UI (surveys, navigation, promo blocks).
# It is very frequent but has little value for careful DeepL translation.
UI_RE = re.compile(
    "お役に立てた|そう思う|そう思わない|どちらともいえない|今後の改善|"
    "さらに詳しく|取扱説明書トップ|このページを見ている人|recommend_list|"
    "アンケート|ページの先頭|サイト内検索|検証用"
)


def manifest_years(paths: Paths, car: str) -> list[str]:
    years = []
    for path in paths.manifests.glob(f"{car}-*.json"):
        year = path.stem.rsplit("-", 1)[-1]
        if year.isdigit():
            years.append(year)
    return sorted(set(years), reverse=True)


def _visible(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def collect_frequencies(paths: Paths, car: str, years: list[str]) -> dict:
    """Count every translation block across all pages of the given years."""
    rows: dict[str, dict] = {}
    started = time.time()
    for year in years:
        site = Site(car=car, year=year)
        try:
            manifest = load_manifest(paths, site)
        except SystemExit:
            log.warning("%s: манифеста нет, пропускаю", year)
            continue
        raw_dir = paths.raw / car / year
        pages = 0
        for page in manifest["pages"]:
            if page.get("status") == "error":
                continue
            path = raw_dir / page["path"]
            if not path.exists():
                continue
            soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")
            seen: set[str] = set()
            items = []
            for seg in collect_html(soup):
                items.append((seg.key, "html", seg.html, _visible(seg.html)))
            for unit in collect_plain(soup):
                items.append((unit.key, "plain", unit.text, unit.text))
            for key, kind, html, text in items:
                row = rows.get(key)
                if row is None:
                    row = {
                        "key": key, "kind": kind, "html": html, "text": text,
                        "count": 0, "pages": 0,
                        "chars": len(html), "text_chars": len(text),
                        "years": {},
                    }
                    rows[key] = row
                row["count"] += 1
                row["years"][year] = row["years"].get(year, 0) + 1
                if key not in seen:
                    seen.add(key)
                    row["pages"] += 1
            pages += 1
        log.info("%s: %d страниц, всего блоков %d", year, pages,
                 sum(r["count"] for r in rows.values()))
    log.info("частотность: %d уникальных блоков за %.1f с",
             len(rows), time.time() - started)
    return {
        "site": {"car": car},
        "years": years,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "unique": len(rows),
        "occurrences": sum(r["count"] for r in rows.values()),
        "chars": sum(r["chars"] for r in rows.values()),
        "rows": rows,
    }


def save_frequencies(paths: Paths, car: str, data: dict) -> Path:
    out = paths.data / "frequencies"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{car}.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def load_frequencies(paths: Paths, car: str) -> dict | None:
    path = paths.data / "frequencies" / f"{car}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def select(rows: dict, min_count: int = 1, min_chars: int = 0,
           max_chars: int | None = None, content_only: bool = False) -> list[dict]:
    result = []
    for row in rows.values():
        row.setdefault("text_chars", len(row["text"]))
        if row["count"] < min_count:
            continue
        if row["text_chars"] < min_chars:
            continue
        if max_chars is not None and row["text_chars"] > max_chars:
            continue
        if content_only and UI_RE.search(row["text"]):
            continue
        result.append(row)
    result.sort(key=lambda r: (-r["count"], -r["text_chars"], r["text"]))
    return result


def plan(rows: list[dict], budget: int) -> tuple[list[dict], int, int, int]:
    """Take rows in order, skipping ones that no longer fit the budget."""
    chosen, used, skipped = [], 0, 0
    for row in rows:
        if used + row["text_chars"] > budget:
            skipped += 1
            continue
        chosen.append(row)
        used += row["text_chars"]
    return chosen, used, sum(r["count"] for r in chosen), skipped


def cumulative(rows: list[dict], stops: list[int]) -> list[dict]:
    out = []
    used = 0
    for i, row in enumerate(rows, 1):
        used += row["text_chars"]
        if i in stops:
            out.append({"rank": i, "chars": used,
                        "occurrences": sum(r["count"] for r in rows[:i])})
    return out
