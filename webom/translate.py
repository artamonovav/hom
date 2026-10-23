from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from .blocks import (
    CJK_RE, HtmlSegment, PlainUnit, apply_translations, collect_html, collect_plain,
    fallback_text_units, key_for, tag_signature,
)
from .config import PROJECT_DIR, Paths, Site, year_dir
from .crawl import load_manifest
from .providers import BaseProvider, TranslationError, get_provider

log = logging.getLogger(__name__)

MENU_RE = re.compile(r"var MENU\s*=\s*(\".*?\");", re.S)


@dataclass
class Job:
    name: str
    soup: BeautifulSoup
    segments: list[HtmlSegment]
    plain: list[PlainUnit]
    out_path: Path | None = None
    is_menu: bool = False


def open_db(paths: Paths) -> sqlite3.Connection:
    conn = sqlite3.connect(paths.db)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS translations ("
        " provider TEXT NOT NULL, target TEXT NOT NULL, src_hash TEXT NOT NULL,"
        " source TEXT NOT NULL, translated TEXT NOT NULL, updated TEXT NOT NULL,"
        " PRIMARY KEY (provider, target, src_hash))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS pages ("
        " url TEXT NOT NULL, target TEXT NOT NULL, status TEXT, blocks INTEGER,"
        " translated INTEGER, updated TEXT, PRIMARY KEY (url, target))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS overrides ("
        " target TEXT NOT NULL, src_hash TEXT NOT NULL, source TEXT NOT NULL,"
        " translated TEXT NOT NULL, provider TEXT NOT NULL, updated TEXT NOT NULL,"
        " PRIMARY KEY (target, src_hash))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS deepl_failures ("
        " target TEXT NOT NULL, src_hash TEXT NOT NULL, source TEXT NOT NULL,"
        " reason TEXT NOT NULL, updated TEXT NOT NULL,"
        " PRIMARY KEY (target, src_hash))"
    )
    conn.commit()
    return conn


def _cache_get(conn, provider: str, target: str, keys: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    if not keys:
        return result
    for i in range(0, len(keys), 500):
        chunk = keys[i:i + 500]
        placeholders = ",".join("?" * len(chunk))
        rows = conn.execute(
            f"SELECT src_hash, translated FROM translations"
            f" WHERE provider=? AND target=? AND src_hash IN ({placeholders})",
            [provider, target, *chunk],
        )
        result.update(dict(rows))
    return result


def load_overrides(conn: sqlite3.Connection, target: str) -> dict[str, str]:
    return dict(conn.execute(
        "SELECT src_hash, translated FROM overrides WHERE target=?", (target,)))


def put_overrides(conn: sqlite3.Connection, target: str, provider: str,
                  items: list[tuple[str, str, str]]) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany(
        "INSERT OR REPLACE INTO overrides"
        " (target, src_hash, source, translated, provider, updated)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [(target, key, src, dst, provider, now) for key, src, dst in items],
    )
    conn.commit()


def load_failures(conn: sqlite3.Connection, target: str) -> set[str]:
    return {key for (key,) in conn.execute(
        "SELECT src_hash FROM deepl_failures WHERE target=?", (target,))}


def put_failures(conn: sqlite3.Connection, target: str,
                 items: list[tuple[str, str, str]]) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany(
        "INSERT OR REPLACE INTO deepl_failures"
        " (target, src_hash, source, reason, updated) VALUES (?, ?, ?, ?, ?)",
        [(target, key, src, reason, now) for key, src, reason in items],
    )
    conn.commit()


def clear_failures(conn: sqlite3.Connection, target: str, keys: list[str]) -> None:
    if keys:
        conn.executemany(
            "DELETE FROM deepl_failures WHERE target=? AND src_hash=?",
            [(target, key) for key in keys],
        )
        conn.commit()


def _cache_put(conn, provider: str, target: str, items: list[tuple[str, str, str]]) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany(
        "INSERT OR REPLACE INTO translations"
        " (provider, target, src_hash, source, translated, updated)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [(provider, target, key, src, dst, now) for key, src, dst in items],
    )
    conn.commit()


PROTECT_TERMS = [
    ("FREED+", "[[Z0]]"),
    ("FREED", "[[Z1]]"),
    ("Honda Sensing", "[[Z2]]"),
    ("Honda", "[[Z3]]"),
    ("internavi", "[[Z4]]"),
    ("Apple CarPlay", "[[Z5]]"),
    ("Android Auto", "[[Z6]]"),
    ("Bluetooth", "[[Z7]]"),
]
_PROTECT_RE = {term: token for term, token in PROTECT_TERMS}
_UNPROTECT = {token: term for term, token in PROTECT_TERMS}
_LEFTOVER_RE = re.compile(r"\[\[Z\d+\]\]")


def _protect(text: str) -> str:
    for term, token in PROTECT_TERMS:
        text = text.replace(term, token)
    return text


def _restore(text: str) -> str:
    for token, term in _UNPROTECT.items():
        text = text.replace(token, term)
    return text


def _norm_text(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", value))


JAPANESE_RE = re.compile(r"[\u3041-\u3096\u30a1-\u30fa\u30fc\u4e00-\u9fff]")


def _bad_translation(source: str, translated: str) -> bool:
    plain = _norm_text(source)
    result = _norm_text(str(translated))
    return bool(
        not str(translated).strip()
        or _LEFTOVER_RE.search(str(translated))
        or (_LEFTOVER_RE.search(plain) is None and JAPANESE_RE.search(plain)
            and JAPANESE_RE.search(result))
    )


def _purge_bad_cache(conn: sqlite3.Connection) -> int:
    """Drop empty replies and replies that are just the Japanese source."""
    rows = conn.execute("SELECT src_hash, source, translated FROM translations").fetchall()
    bad: list[str] = []
    for src_hash, source, translated in rows:
        plain = _norm_text(source)
        result = _norm_text(str(translated))
        if not str(translated).strip():
            bad.append(src_hash)
        elif JAPANESE_RE.search(plain) and (JAPANESE_RE.search(result)
                                            or _LEFTOVER_RE.search(str(translated))):
            bad.append(src_hash)
    if bad:
        conn.executemany("DELETE FROM translations WHERE src_hash = ?", [(h,) for h in bad])
        conn.commit()
        log.info("удалено из кэша пустых/непереведённых фрагментов: %d", len(bad))
    return len(bad)


def _retry_single(provider: BaseProvider, target: str, text: str) -> str | None:
    for attempt in range(3):
        try:
            result = provider.translate([_protect(text)], tgt=target)
        except TranslationError as exc:
            log.debug("повтор не удался: %s", exc)
            result = []
        if result:
            candidate = _restore(result[0])
            if candidate.strip() and not _LEFTOVER_RE.search(candidate):
                return candidate
        time.sleep(1.0 + attempt)
    return None


def _translate_items(provider: BaseProvider, target: str,
                     conn: sqlite3.Connection,
                     items: list[tuple[str, str]]) -> tuple[int, int]:
    """Translate (key, source) pairs, saving progress. Returns (ok, failed)."""
    if not items:
        return 0, 0
    ok = failed = 0
    batch: list[tuple[str, str]] = []
    chars = 0

    def store(pairs: list[tuple[str, str]], translations: list[str]) -> None:
        nonlocal ok, failed
        good: list[tuple[str, str, str]] = []
        bad: list[tuple[str, str]] = []
        for (key, src), dst in zip(pairs, translations):
            if _bad_translation(src, str(dst)):
                bad.append((key, src))
            else:
                good.append((key, src, dst))
        if good:
            _cache_put(conn, provider.name, target, good)
            ok += len(good)
        for key, src in bad:
            dst = _retry_single(provider, target, src)
            if dst is None or _bad_translation(src, dst):
                log.warning("пустой/неизменённый перевод: %s", src[:60])
                failed += 1
            else:
                _cache_put(conn, provider.name, target, [(key, src, dst)])
                ok += 1
        if ok and ok % 200 < len(pairs):
            log.info("переведено фрагментов: %d", ok)

    def process(pairs: list[tuple[str, str]]) -> None:
        nonlocal failed
        sources = [src for _, src in pairs]
        protected = [_protect(src) for src in sources]
        try:
            translations = provider.translate(protected, tgt=target)
            translations = [_restore(t) for t in translations]
        except TranslationError as exc:
            if len(pairs) == 1:
                log.warning("перевод не удался: %s | %s", exc, pairs[0][1][:60])
                failed += 1
                return
            mid = max(1, len(pairs) // 2)
            process(pairs[:mid])
            process(pairs[mid:])
            return
        if len(translations) != len(pairs):
            log.warning("провайдер вернул %d переводов на %d фрагментов",
                        len(translations), len(pairs))
            if len(pairs) == 1:
                failed += 1
            else:
                mid = max(1, len(pairs) // 2)
                process(pairs[:mid])
                process(pairs[mid:])
            return
        store(pairs, translations)

    for pair in items:
        text = pair[1]
        if batch and (len(batch) >= provider.max_items or chars + len(text) > provider.max_chars):
            process(batch)
            batch, chars = [], 0
        batch.append(pair)
        chars += len(text)
    if batch:
        process(batch)
    return ok, failed


def _apply_glossary(lookup: dict[str, str], target: str) -> dict[str, str]:
    path = PROJECT_DIR / "glossary" / f"{target}.json"
    if not path.exists():
        return lookup
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("глоссарий %s не прочитан: %s", path, exc)
        return lookup
    rules = [(str(a), str(b)) for a, b in data.get("replacements", []) if a]
    if not rules:
        return lookup
    return {k: _replace_all(v, rules) for k, v in lookup.items()}


def _replace_all(text: str, rules: list[tuple[str, str]]) -> str:
    for bad, good in rules:
        text = text.replace(bad, good)
    return text


def _menu_source(paths: Paths, site: Site) -> tuple[str, str] | None:
    from .assets import asset_file
    js = asset_file(paths, site, "js/url.js")
    if not js.exists():
        return None
    text = js.read_text(encoding="utf-8", errors="replace")
    m = MENU_RE.search(text)
    if not m:
        return None
    try:
        menu = json.loads(m.group(1))
    except ValueError:
        return None
    return text, menu


def _translate_data_files(manifest: dict, raw_dir: Path, out_dir: Path,
                          provider: BaseProvider, target: str,
                          conn: sqlite3.Connection) -> dict:
    """Translate the side-menu titles stored in ``contentsDB.json`` files."""
    fields = ("L1", "L2", "L3", "L4", "L5", "UnitName")
    documents: list[tuple[str, dict]] = []
    sources: dict[str, str] = {}

    for rel in manifest.get("data_files", []):
        path = raw_dir / rel
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            log.warning("JSON меню %s: %s", rel, exc)
            continue
        entries = data.get("ContentsList") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            for field in fields:
                value = entry.get(field)
                if isinstance(value, str) and value.strip() and CJK_RE.search(value):
                    sources.setdefault(key_for(value, "text:"), value)
        documents.append((rel, data))

    if not documents:
        return {"files": 0, "titles": 0, "failed": 0}

    cached = _cache_get(conn, provider.name, target, list(sources))
    missing = [(key, text) for key, text in sources.items() if key not in cached]
    log.info("меню JSON: %d заголовков, к переводу: %d", len(sources), len(missing))
    ok, failed = _translate_items(provider, target, conn, missing)
    lookup = _cache_get(conn, provider.name, target, list(sources))
    lookup.update(cached)
    lookup = _apply_glossary(lookup, target)
    lookup.update(load_overrides(conn, target))

    for rel, data in documents:
        for entry in data.get("ContentsList", []):
            for field in fields:
                value = entry.get(field)
                if not isinstance(value, str) or not value:
                    continue
                translated = lookup.get(key_for(value, "text:"))
                if translated:
                    entry[field] = translated
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"files": len(documents), "titles": len(sources),
            "translated": ok, "failed": failed}


def translate_year(site: Site, paths: Paths, provider_name: str = "google-web",
                   target: str = "ru", limit: int | None = None,
                   src: str = "ja") -> dict:
    manifest = load_manifest(paths, site)
    raw_dir = year_dir(paths, site, "raw")
    out_dir = paths.translated / target / site.car / site.year
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = [p for p in manifest["pages"] if p.get("status") != "error"]
    if limit:
        pages = pages[:limit]

    jobs: list[Job] = []
    for page in pages:
        html = (raw_dir / page["path"]).read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        segments = collect_html(soup)
        plain = collect_plain(soup)
        jobs.append(Job(page["url"], soup, segments, plain, out_dir / page["path"]))

    menu_job: Job | None = None
    menu_info = _menu_source(paths, site)
    if menu_info:
        _, menu_html = menu_info
        menu_soup = BeautifulSoup(menu_html, "html.parser")
        menu_job = Job("__menu__", menu_soup, collect_html(menu_soup),
                       collect_plain(menu_soup), out_dir / "menu.html", is_menu=True)
        jobs.append(menu_job)

    provider = get_provider(provider_name)
    conn = open_db(paths)
    _purge_bad_cache(conn)

    # Gather unique sources.
    sources: dict[str, str] = {}
    for job in jobs:
        for seg in job.segments:
            sources.setdefault(seg.key, seg.html)
        for unit in job.plain:
            sources.setdefault(unit.key, unit.text)

    log.info("страниц: %d, уникальных фрагментов: %d", len(pages), len(sources))
    cached = _cache_get(conn, provider.name, target, list(sources))
    missing = [(k, sources[k]) for k in sources if k not in cached]
    total_chars = sum(len(s) for s in sources.values())
    log.info("в кэше: %d, к переводу: %d (%.1f тыс. знаков)",
             len(cached), len(missing), total_chars / 1000)

    ok, failed = _translate_items(provider, target, conn, missing)
    log.info("перевод: ok=%d, ошибок=%d", ok, failed)

    lookup = _cache_get(conn, provider.name, target, list(sources))
    lookup.update({k: v for k, v in cached.items()})
    lookup = _apply_glossary(lookup, target)
    overrides = load_overrides(conn, target)
    overrides_used = sum(1 for key in sources if key in overrides)
    if overrides_used:
        log.info("DeepL overrides: %d из %d блоков", overrides_used, len(sources))
    lookup.update(overrides)

    # Fallback for blocks whose markup was damaged by the provider.
    fallback_items: list[tuple[str, str]] = []
    seen_fallback: set[str] = set()
    for job in jobs:
        for seg in job.segments:
            translated = lookup.get(seg.key)
            if translated is None:
                seg.valid = False
                units = fallback_text_units(seg)
                job.plain.extend(units)
                for unit in units:
                    if unit.key not in lookup and unit.key not in seen_fallback:
                        seen_fallback.add(unit.key)
                        fallback_items.append((unit.key, unit.text))
                continue
            plain_src = _norm_text(seg.html)
            unchanged = (_norm_text(translated) == plain_src
                         and bool(JAPANESE_RE.search(plain_src)))
            residual = bool(JAPANESE_RE.search(_norm_text(translated)))
            if tag_signature(translated) != tag_signature(seg.html) or unchanged or residual:
                seg.valid = False
                units = fallback_text_units(seg)
                job.plain.extend(units)
                for unit in units:
                    if unit.key not in lookup and unit.key not in seen_fallback:
                        seen_fallback.add(unit.key)
                        fallback_items.append((unit.key, unit.text))
    if fallback_items:
        log.info("повреждённая разметка: %d блоков, перевожу по текстовым узлам", len(fallback_items))
        _translate_items(provider, target, conn, fallback_items)
        lookup.update(_cache_get(conn, provider.name, target, [k for k, _ in fallback_items]))
        lookup = _apply_glossary(lookup, target)
        lookup.update(overrides)

    # Apply and write pages.
    stats = {"pages": 0, "segments": 0, "plain": 0, "missing": 0, "fallback_blocks": 0}
    menu_out = None
    for job in jobs:
        active_segments = [s for s in job.segments if s.valid]
        before_missing = stats["missing"]
        result = apply_translations(job.soup, active_segments, lookup, job.plain)
        stats["segments"] += result["html"]
        stats["plain"] += result["plain"]
        stats["missing"] += result["missing"]
        stats["fallback_blocks"] += result["html_fallback"]

        html = str(job.soup)
        if job.is_menu:
            menu_out = html
            (out_dir / "menu.html").write_text(html, encoding="utf-8")
        else:
            job.out_path.parent.mkdir(parents=True, exist_ok=True)
            job.out_path.write_text(html, encoding="utf-8")
            stats["pages"] += 1
            conn.execute(
                "INSERT OR REPLACE INTO pages (url, target, status, blocks, translated, updated)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (job.name, target, "ok",
                 len(job.segments) + len(job.plain),
                 result["html"] + result["plain"],
                 datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
    conn.commit()

    data_info = _translate_data_files(manifest, raw_dir, out_dir, provider, target, conn)

    # Tooltips and labels stored outside HTML: visualindex_content.json for
    # 2025/2026 and the old appearance/interior point data JS files.
    from .data_translate import translate_data_year
    data_translation = translate_data_year(site, paths, provider_name, target)

    report = {
        "site": {"car": site.car, "year": site.year},
        "target": target,
        "provider": provider.name,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pages": stats["pages"],
        "unique_sources": len(sources),
        "source_chars": total_chars,
        "translated_now": ok,
        "failed": failed,
        "cached": len(cached),
        "overrides_applied": overrides_used,
        "applied_segments": stats["segments"],
        "applied_plain": stats["plain"],
        "missing": stats["missing"],
        "fallback_blocks": stats["fallback_blocks"],
        "menu_translated": menu_out is not None,
        "menu_json_files": data_info["files"],
        "menu_json_titles": data_info["titles"],
        "menu_json_failed": data_info.get("failed", 0),
        "data_files": data_translation,
    }
    paths.reports.mkdir(parents=True, exist_ok=True)
    report_path = paths.reports / f"translation-{site.car}-{site.year}-{target}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("готово: %s", report_path)
    return report
