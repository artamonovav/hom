from __future__ import annotations

import logging
import os
import re

import requests

from .config import Paths
from .freq import collect_frequencies, load_frequencies, plan, save_frequencies, select
from .providers import QuotaExceeded, TranslationError, get_provider
from .translate import (
    _bad_translation, _protect, _restore, clear_failures, load_failures,
    load_overrides, open_db, put_failures, put_overrides,
)
from .blocks import tag_signature

log = logging.getLogger(__name__)


def deepl_usage() -> dict | None:
    """Return the current DeepL quota (character_count / character_limit)."""
    key = os.environ.get("DEEPL_API_KEY")
    if not key:
        return None
    host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
    try:
        resp = requests.get(f"https://{host}/v2/usage",
                            headers={"Authorization": f"DeepL-Auth-Key {key}"},
                            timeout=30)
        if resp.status_code != 200:
            log.warning("deepl usage: HTTP %s: %s", resp.status_code, resp.text[:200])
            return None
        return resp.json()
    except requests.RequestException as exc:
        log.warning("deepl usage: %s", exc)
        return None


def _chunks(rows: list[dict], max_items: int, max_chars: int):
    batch, chars = [], 0
    for row in rows:
        size = row["chars"]
        if batch and (len(batch) >= max_items or chars + size > max_chars):
            yield batch
            batch, chars = [], 0
        batch.append(row)
        chars += size
    if batch:
        yield batch


def translate_top(paths: Paths, car: str, years: list[str], budget: int | None,
                  min_count: int = 1, min_chars: int = 0, top: int | None = None,
                  content_only: bool = True, dry_run: bool = False,
                  refresh: bool = False, retry_failed: bool = False) -> dict:
    data = None if refresh else load_frequencies(paths, car)
    if data is None or set(data.get("years", [])) != set(years):
        data = collect_frequencies(paths, car, years)
        save_frequencies(paths, car, data)

    rows = select(data["rows"], min_count=min_count, min_chars=min_chars,
                  content_only=content_only)
    conn = open_db(paths)
    done = load_overrides(conn, "ru")
    known = set() if retry_failed else load_failures(conn, "ru")
    rows = [r for r in rows if r["key"] not in done and r["key"] not in known]
    if top:
        rows = rows[:top]

    if budget == "auto":
        usage = deepl_usage()
        if usage is None:
            if dry_run:
                budget = 500_000
                log.warning("DeepL недоступен: для плана принята квота 500000 знаков")
            else:
                raise SystemExit("Не удалось узнать остаток DeepL. Задайте --budget N.")
        else:
            remaining = max(0, usage["character_limit"] - usage["character_count"])
            budget = max(0, remaining - 1000)
            log.info("DeepL: использовано %d из %d, доступно %d знаков",
                     usage["character_count"], usage["character_limit"], remaining)

    chosen, used, occurrences, skipped = plan(rows, budget)
    result = {
        "candidates": len(rows),
        "selected": len(chosen),
        "chars_planned": used,
        "budget": budget,
        "occurrences": occurrences,
        "skipped": skipped,
        "known_failures": len(known),
        "translated": 0,
        "failed": 0,
        "chars_sent": 0,
    }
    if dry_run or not chosen:
        return result

    provider = get_provider("deepl")
    sent = failed = new_count = 0
    bad: list[tuple[str, str, str]] = []
    for batch in _chunks(chosen, provider.max_items, provider.max_chars):
        protected = [_protect(row["html"]) for row in batch]
        try:
            translations = provider.translate(protected, tgt="ru")
        except QuotaExceeded as exc:
            log.error("DeepL: квота исчерпана: %s", exc)
            result["quota_exceeded"] = True
            break
        except TranslationError as exc:
            log.warning("DeepL: пакет не прошёл (%s), повторяю по одному", exc)
            translations = []
            for src in protected:
                try:
                    translations.append(provider.translate([src], tgt="ru")[0])
                except QuotaExceeded as one:
                    log.error("DeepL: квота исчерпана: %s", one)
                    result["quota_exceeded"] = True
                    translations = []
                    break
                except TranslationError as one:
                    log.warning("DeepL: фрагмент не переведён: %s", one)
                    translations.append("")
            if result.get("quota_exceeded"):
                break
        good: list[tuple[str, str, str]] = []
        for row, src, dst in zip(batch, protected, translations):
            dst = _restore(dst)
            if _bad_translation(row["html"], dst):
                log.warning("DeepL: плохой перевод: %s", row["text"][:60])
                failed += 1
                bad.append((row["key"], row["html"], "bad translation"))
                continue
            if row["kind"] == "html" and tag_signature(row["html"]) != tag_signature(dst):
                log.warning("DeepL: изменена разметка: %s", row["text"][:60])
                failed += 1
                bad.append((row["key"], row["html"], "markup changed"))
                continue
            good.append((row["key"], row["html"], dst))
        if good:
            put_overrides(conn, "ru", provider.name, good)
            clear_failures(conn, "ru", [key for key, _, _ in good])
            new_count += len(good)
        batch_chars = sum(row["text_chars"] for row in batch)
        sent += batch_chars
        log.info("DeepL: %d/%d, отправлено %d знаков", len(good), len(batch), batch_chars)

    if bad:
        put_failures(conn, "ru", bad)
    result["translated"] = new_count
    result["failed"] = failed
    result["chars_sent"] = sent
    return result


def translate_menus(paths: Paths, car: str, years: list[str], budget: int | None,
                    dry_run: bool = False, retry_failed: bool = False) -> dict:
    """Translate side-menu titles from contentsDB.json files into overrides."""
    import json as _json

    from bs4 import BeautifulSoup

    from .blocks import CJK_RE, collect_html, collect_plain, key_for, tag_signature
    from .config import Site
    from .crawl import load_manifest
    from .translate import _menu_source

    fields = ("L1", "L2", "L3", "L4", "L5", "UnitName")
    sources: dict[str, str] = {}
    html_keys: set[str] = set()
    for year in years:
        site = Site(car=car, year=year)
        try:
            manifest = load_manifest(paths, site)
        except SystemExit:
            continue
        for rel in manifest.get("data_files", []):
            path = paths.raw / car / year / rel
            if not path.exists():
                continue
            try:
                data = _json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                continue
            for entry in data.get("ContentsList", []) if isinstance(data, dict) else []:
                for field in fields:
                    value = entry.get(field)
                    if isinstance(value, str) and value.strip() and CJK_RE.search(value):
                        sources.setdefault(key_for(value, "text:"), value)
        # Old-style manuals keep the side menu in js/url.js.
        menu = _menu_source(paths, site)
        if menu:
            soup = BeautifulSoup(menu[1], "html.parser")
            for segment in collect_html(soup):
                sources.setdefault(segment.key, segment.html)
                html_keys.add(segment.key)
            for unit in collect_plain(soup):
                sources.setdefault(unit.key, unit.text)

    conn = open_db(paths)
    done = load_overrides(conn, "ru")
    known = set() if retry_failed else load_failures(conn, "ru")
    rows = [
        {"key": key, "html": text, "text": text,
         "kind": "html" if key in html_keys else "plain",
         "chars": len(text), "text_chars": len(text), "count": 1}
        for key, text in sources.items() if key not in done and key not in known
    ]
    if budget == "auto":
        usage = deepl_usage()
        if usage is None:
            if dry_run:
                budget = 500_000
            else:
                raise SystemExit("Не удалось узнать остаток DeepL. Задайте --budget N.")
        else:
            budget = max(0, usage["character_limit"] - usage["character_count"] - 1000)
    chosen, used, _, _ = plan(rows, budget)
    result = {"candidates": len(rows), "selected": len(chosen),
              "chars_planned": used, "translated": 0, "failed": 0}
    if dry_run or not chosen:
        return result

    provider = get_provider("deepl")
    for batch in _chunks(chosen, provider.max_items, provider.max_chars):
        protected = [_protect(row["html"]) for row in batch]
        try:
            translations = provider.translate(protected, tgt="ru")
        except QuotaExceeded as exc:
            log.error("DeepL: квота исчерпана: %s", exc)
            result["quota_exceeded"] = True
            break
        except TranslationError as exc:
            log.error("DeepL: %s", exc)
            result["failed"] += len(batch)
            continue
        good = []
        bad = []
        for row, dst in zip(batch, translations):
            dst = _restore(dst)
            if _bad_translation(row["html"], dst):
                result["failed"] += 1
                bad.append((row["key"], row["html"], "bad translation"))
                continue
            if row["kind"] == "html" and tag_signature(row["html"]) != tag_signature(dst):
                result["failed"] += 1
                bad.append((row["key"], row["html"], "markup changed"))
                continue
            good.append((row["key"], row["html"], dst))
        if good:
            put_overrides(conn, "ru", provider.name, good)
            clear_failures(conn, "ru", [key for key, _, _ in good])
        if bad:
            put_failures(conn, "ru", bad)
        log.info("DeepL меню: %d/%d", len(good), len(batch))
    result["translated"] = len(load_overrides(conn, "ru")) - len(done)
    return result


def _encode_tags(html: str) -> tuple[str, list[str]]:
    tags: list[str] = []

    def repl(match):
        tags.append(match.group(0))
        return f"[[T{len(tags) - 1}]]"

    return re.sub(r"<[^>]+>", repl, html), tags


def _decode_tags(text: str, tags: list[str]) -> str:
    for index, tag in enumerate(tags):
        text = text.replace(f"[[T{index}]]", tag)
    return text


def salvage_failed(paths: Paths, car: str, years: list[str], budget: int | None,
                   min_chars: int = 20, max_tags: int = 4,
                   dry_run: bool = False) -> dict:
    """Retry markup-failed blocks, protecting tags as plain-text placeholders."""
    from .blocks import tag_structure

    data = load_frequencies(paths, car)
    if data is None or set(data.get("years", [])) != set(years):
        data = collect_frequencies(paths, car, years)
        save_frequencies(paths, car, data)

    conn = open_db(paths)
    done = load_overrides(conn, "ru")
    failed = load_failures(conn, "ru")
    rows = []
    for row in data["rows"].values():
        if (row["key"] in failed and row["key"] not in done
                and row["kind"] == "html" and row["text_chars"] >= min_chars
                and len(re.findall(r"<[^>]+>", row["html"])) <= max_tags):
            rows.append(row)
    rows.sort(key=lambda row: (-row["count"], -row["text_chars"]))

    if budget == "auto":
        usage = deepl_usage()
        if usage is None:
            if dry_run:
                budget = 500_000
            else:
                raise SystemExit("Не удалось узнать остаток DeepL. Задайте --budget N.")
        else:
            budget = max(0, usage["character_limit"] - usage["character_count"] - 1000)
    chosen, used, occurrences, _ = plan(rows, budget)
    result = {"candidates": len(rows), "selected": len(chosen),
              "chars_planned": used, "occurrences": occurrences,
              "translated": 0, "failed": 0, "chars_sent": 0}
    if dry_run or not chosen:
        return result

    provider = get_provider("deepl")
    sent = translated = failed_count = 0
    for batch in _chunks(chosen, provider.max_items, provider.max_chars):
        encoded = []
        tags = []
        for row in batch:
            text, items = _encode_tags(row["html"])
            encoded.append(_protect(text))
            tags.append(items)
        try:
            outputs = provider.translate(encoded, tgt="ru")
        except QuotaExceeded as exc:
            log.error("DeepL: квота исчерпана: %s", exc)
            result["quota_exceeded"] = True
            break
        except TranslationError as exc:
            log.error("DeepL: %s", exc)
            failed_count += len(batch)
            continue
        good = []
        for row, output, items in zip(batch, outputs, tags):
            dst = _decode_tags(_restore(output), items)
            if "[[" in dst:
                failed_count += 1
                log.warning("DeepL: не восстановлены теги: %s", row["text"][:60])
                continue
            if _bad_translation(row["html"], dst):
                failed_count += 1
                continue
            if tag_structure(row["html"]) != tag_structure(dst):
                failed_count += 1
                log.warning("DeepL: сдвинута структура тегов: %s", row["text"][:60])
                continue
            good.append((row["key"], row["html"], dst))
        if good:
            put_overrides(conn, "ru", provider.name, good)
            clear_failures(conn, "ru", [key for key, _, _ in good])
            translated += len(good)
        sent += sum(row["text_chars"] for row in batch)
        log.info("DeepL salvage: %d/%d", len(good), len(batch))
    result["translated"] = translated
    result["failed"] = failed_count
    result["chars_sent"] = sent
    return result
