from __future__ import annotations

import hashlib
import re
import warnings
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, NavigableString, Tag
from bs4 import MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "body", "caption", "center",
    "col", "colgroup", "dd", "details", "dialog", "div", "dl", "dt", "fieldset",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
    "h6", "header", "hgroup", "hr", "html", "legend", "li", "main", "menu",
    "nav", "ol", "optgroup", "option", "p", "pre", "section", "summary",
    "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}

INLINE_TAGS = {
    "a", "abbr", "b", "bdi", "bdo", "br", "button", "cite", "code", "data",
    "del", "dfn", "em", "i", "img", "input", "ins", "kbd", "label", "mark",
    "q", "rp", "rt", "ruby", "s", "samp", "select", "small", "span", "strong",
    "sub", "sup", "time", "u", "var", "wbr",
}

SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "canvas", "iframe"}

CJK_RE = re.compile(r"[\u3005\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def key_for(text: str, kind: str) -> str:
    return hashlib.sha256(f"{kind}\x00{text}".encode("utf-8")).hexdigest()


@dataclass
class HtmlSegment:
    parent: Tag
    nodes: list
    html: str
    key: str = field(init=False)
    valid: bool = True
    fallback_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.key = key_for(self.html, "html")


@dataclass
class PlainUnit:
    element: object            # Tag or NavigableString
    text: str
    kind: str                  # title | meta | alt | placeholder | text | attr
    attr: str | None = None
    key: str = field(init=False)

    def __post_init__(self) -> None:
        self.key = key_for(self.text, f"{self.kind}:{self.attr or ''}")


def _visible_text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def collect_html(soup: BeautifulSoup) -> list[HtmlSegment]:
    segments: list[HtmlSegment] = []

    def flush(parent: Tag, run: list) -> None:
        if not run:
            return
        while run and isinstance(run[0], NavigableString) and not str(run[0]).strip():
            run.pop(0)
        while run and isinstance(run[-1], NavigableString) and not str(run[-1]).strip():
            run.pop()
        if not run:
            return
        html = "".join(str(n) for n in run)
        text = _visible_text(html)
        if not text.strip() or not has_cjk(text):
            return
        segments.append(HtmlSegment(parent=parent, nodes=list(run), html=html))

    def walk(el: Tag) -> None:
        run: list = []
        for child in list(el.children):
            if isinstance(child, NavigableString):
                run.append(child)
            elif isinstance(child, Tag):
                if child.name in SKIP_TAGS:
                    continue
                if child.name in INLINE_TAGS:
                    run.append(child)
                elif child.name in BLOCK_TAGS:
                    flush(el, run)
                    run = []
                    walk(child)
                else:
                    run.append(child)
        flush(el, run)

    body = soup.body or soup
    walk(body)
    return segments


def collect_plain(soup: BeautifulSoup) -> list[PlainUnit]:
    units: list[PlainUnit] = []

    if soup.title and soup.title.string and has_cjk(soup.title.string):
        units.append(PlainUnit(soup.title, soup.title.string, "title"))

    for meta in soup.find_all("meta"):
        content = meta.get("content")
        if content and meta.get("name") == "description" and has_cjk(content):
            units.append(PlainUnit(meta, content, "meta", "content"))

    for img in soup.find_all("img"):
        alt = img.get("alt")
        if alt and has_cjk(alt):
            units.append(PlainUnit(img, alt, "alt", "alt"))

    for tag in soup.find_all(["input", "textarea"]):
        ph = tag.get("placeholder")
        if ph and has_cjk(ph):
            units.append(PlainUnit(tag, ph, "placeholder", "placeholder"))

    for tag in soup.find_all(attrs={"title": True}):
        title = tag.get("title")
        if title and has_cjk(title):
            units.append(PlainUnit(tag, title, "attr", "title"))

    return units


def fallback_text_units(segment: HtmlSegment) -> list[PlainUnit]:
    units: list[PlainUnit] = []
    for node in segment.nodes:
        for text_node in _iter_text_nodes(node):
            value = str(text_node)
            if value.strip() and has_cjk(value):
                units.append(PlainUnit(text_node, value, "text"))
    return units


def _iter_text_nodes(node):
    if isinstance(node, NavigableString):
        yield node
        return
    if isinstance(node, Tag):
        if node.name in SKIP_TAGS:
            return
        for child in node.children:
            yield from _iter_text_nodes(child)


def tag_signature(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [t.name for t in soup.find_all(True)]


def tag_structure(html: str) -> list[tuple[str, int]]:
    """Tag names with nesting depth, to catch moved/renested inline tags."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[tuple[str, int]] = []

    def walk(node, depth: int = 0) -> None:
        for child in node.children:
            if isinstance(child, Tag):
                out.append((child.name, depth))
                walk(child, depth + 1)

    walk(soup)
    return out


def _restore_attributes(source_html: str, translated_html: str) -> str:
    """Keep the original markup attributes (style, class, href, id, ...).

    Machine translators sometimes localise attribute values, which breaks CSS
    and links; only the visible text should change.
    """
    source = BeautifulSoup(source_html, "html.parser")
    translated = BeautifulSoup(translated_html, "html.parser")
    src_tags = source.find_all(True)
    dst_tags = translated.find_all(True)
    if len(src_tags) != len(dst_tags):
        return translated_html
    text_attrs = {"alt", "title", "placeholder", "value", "aria-label"}
    for src, dst in zip(src_tags, dst_tags):
        if src.name != dst.name:
            return translated_html
        attrs = dict(src.attrs)
        for name in text_attrs:
            if name in dst.attrs:
                attrs[name] = dst.attrs[name]
        dst.attrs = attrs
    return str(translated)


def apply_translations(soup: BeautifulSoup, segments: list[HtmlSegment],
                       lookup: dict[str, str], plain: list[PlainUnit]) -> dict:
    """Replace segments in-place. Returns statistics."""
    stats = {"html": 0, "html_fallback": 0, "plain": 0, "missing": 0}

    for unit in plain:
        translated = lookup.get(unit.key)
        if translated is None:
            stats["missing"] += 1
            continue
        if unit.kind == "title":
            unit.element.string = translated
        elif unit.kind == "text":
            unit.element.replace_with(NavigableString(translated))
        else:
            unit.element[unit.attr] = translated
        stats["plain"] += 1

    # Replace from the end of the document to keep parent indices stable.
    for seg in reversed(segments):
        translated = lookup.get(seg.key)
        if translated is None:
            stats["missing"] += 1
            continue
        if tag_signature(translated) != tag_signature(seg.html):
            stats["html_fallback"] += 1
            continue
        translated = _restore_attributes(seg.html, translated)
        frag = BeautifulSoup(translated, "html.parser")
        new_nodes = list(frag.contents)
        if not new_nodes:
            continue
        parent = seg.parent
        try:
            idx = parent.index(seg.nodes[0])
        except ValueError:
            stats["missing"] += 1
            continue
        for node in list(seg.nodes):
            if getattr(node, "parent", None) is parent:
                node.extract()
        for offset, node in enumerate(new_nodes):
            if getattr(node, "parent", None) is not None:
                node.extract()
            parent.insert(idx + offset, node)
        stats["html"] += 1

    return stats
