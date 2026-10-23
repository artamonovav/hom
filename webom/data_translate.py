from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

from .assets import asset_file
from .blocks import (
    CJK_RE, HtmlSegment, PlainUnit, apply_translations, collect_html, collect_plain,
    fallback_text_units, key_for, tag_signature,
)
from .config import Paths, Site
from .providers import BaseProvider, get_provider
from .translate import (
    _apply_glossary, _bad_translation, _cache_get, _translate_items, load_overrides,
    open_db, put_overrides,
)

log = logging.getLogger(__name__)

CAPTION_RE = re.compile(r'("caption"\s*:\s*)"((?:\\.|[^"\\])*)"')
VISUAL_FILES = (
    "language/ja_JP/main/json/visualindex_content.json",
    "language/ja_JP/main/json/inline.json",
)
POINT_FILES = (
    "pc/js/data/appearance.point.js",
    "pc/js/data/interior.point.js",
)


@dataclass
class Fragment:
    soup: BeautifulSoup
    segments: list[HtmlSegment]
    plain: list[PlainUnit]
    sources: dict[str, str]
    result: str = ""


def _make_fragment(text: str) -> Fragment:
    soup = BeautifulSoup(f"<div>{text}</div>", "html.parser")
    segments = collect_html(soup)
    plain = collect_plain(soup)
    # Translate text nodes, not the whole HTML string.  This keeps inline tags
    # in place and lets DeepL overrides for short labels (for example
    # "コンビニフック") apply even when the label is followed by <sup>✤</sup>.
    for segment in segments:
        plain.extend(fallback_text_units(segment))
    sources = {
        unit.key: unit.text
        for unit in plain
        if CJK_RE.search(unit.text)
    }
    return Fragment(soup, segments, plain, sources)


def _translate_fragments(fragments: list[Fragment], provider: BaseProvider,
                         target: str, conn) -> dict:
    sources: dict[str, str] = {}
    for fragment in fragments:
        sources.update(fragment.sources)
    if not sources:
        return {"sources": 0, "translated": 0, "failed": 0}

    overrides = load_overrides(conn, target)
    cached = _cache_get(conn, provider.name, target, list(sources))
    missing = [(k, v) for k, v in sources.items()
               if k not in cached and k not in overrides]
    ok, failed = _translate_items(provider, target, conn, missing)

    lookup = _cache_get(conn, provider.name, target, list(sources))
    lookup.update(cached)
    lookup = _apply_glossary(lookup, target)
    lookup.update(overrides)

    if provider.name == "deepl":
        good = [(key, src, lookup[key]) for key, src in sources.items() if key in lookup]
        if good:
            put_overrides(conn, target, provider.name, good)

    for fragment in fragments:
        apply_translations(fragment.soup, [], lookup, fragment.plain)
        fragment.result = fragment.soup.div.decode_contents()

    return {"sources": len(sources), "translated": ok, "failed": failed}


def _walk_json_strings(value, setter):
    if isinstance(value, dict):
        for key in list(value.keys()):
            item = value[key]
            if isinstance(item, str) and CJK_RE.search(item):
                setter(value, key, item)
            else:
                _walk_json_strings(item, setter)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, str) and CJK_RE.search(item):
                setter(value, index, item)
            else:
                _walk_json_strings(item, setter)


def _translate_json_file(src: Path, dest: Path, provider: BaseProvider,
                         target: str, conn) -> dict:
    try:
        data = json.loads(src.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        log.warning("data JSON %s: %s", src, exc)
        return {"file": src.name, "sources": 0, "translated": 0, "failed": 0}

    refs: list[tuple[object, object, str]] = []

    def add(container, key, text):
        refs.append((container, key, text))

    _walk_json_strings(data, add)
    fragments = [_make_fragment(text) for _, _, text in refs]
    stats = _translate_fragments(fragments, provider, target, conn)
    for (container, key, _), fragment in zip(refs, fragments):
        container[key] = fragment.result
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("data JSON переведён: %s (%d строк)", dest.relative_to(dest.parents[0]), len(refs))
    return {"file": src.name, **stats, "strings": len(refs)}


def _translate_js_file(src: Path, dest: Path, provider: BaseProvider,
                       target: str, conn) -> dict:
    try:
        text = src.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.warning("data JS %s: %s", src, exc)
        return {"file": src.name, "sources": 0, "translated": 0, "failed": 0}

    matches = list(CAPTION_RE.finditer(text))
    refs: list[tuple[int, str, str]] = []
    for match in matches:
        try:
            decoded = json.loads('"' + match.group(2) + '"')
        except ValueError:
            decoded = match.group(2)
        if CJK_RE.search(decoded):
            refs.append((match.start(2), match.end(2), decoded))
    fragments = [_make_fragment(text) for _, _, text in refs]
    stats = _translate_fragments(fragments, provider, target, conn)

    out = []
    last = 0
    for (start, end, _), fragment in zip(refs, fragments):
        out.append(text[last:start])
        out.append(json.dumps(fragment.result, ensure_ascii=False)[1:-1])
        last = end
    out.append(text[last:])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("".join(out), encoding="utf-8")
    log.info("data JS переведён: %s (%d подписей)", dest.name, len(refs))
    return {"file": src.name, **stats, "strings": len(refs)}


def translate_data_year(site: Site, paths: Paths, provider_name: str = "google-web",
                        target: str = "ru") -> dict:
    provider = get_provider(provider_name)
    conn = open_db(paths)
    out_dir = paths.translated / target / site.car / site.year
    results: list[dict] = []

    for rel in VISUAL_FILES:
        src = asset_file(paths, site, rel)
        if src.exists():
            results.append(_translate_json_file(src, out_dir / rel, provider, target, conn))

    for rel in POINT_FILES:
        src = asset_file(paths, site, rel)
        if src.exists():
            results.append(_translate_js_file(src, out_dir / rel, provider, target, conn))

    total_sources = sum(r.get("sources", 0) for r in results)
    total_ok = sum(r.get("translated", 0) for r in results)
    total_failed = sum(r.get("failed", 0) for r in results)
    log.info("data-файлы: %d, строк: %d, переведено: %d, ошибок: %d",
             len(results), total_sources, total_ok, total_failed)
    return {"files": len(results), "sources": total_sources,
            "translated": total_ok, "failed": total_failed, "details": results}
