from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .config import Paths, Site, year_dir
from .crawl import load_manifest
from .urls import is_skippable, safe_relpath

log = logging.getLogger(__name__)

URL_ATTRS = {
    "a": ("href",),
    "area": ("href",),
    "link": ("href",),
    "img": ("src", "data-src", "data-original"),
    "script": ("src",),
    "source": ("src",),
    "video": ("src", "poster"),
    "audio": ("src",),
    "embed": ("src",),
    "object": ("data",),
    "input": ("src",),
}

EXTERNAL_SCRIPTS = ("beacon", "mf-search", "google-analytics", "googletagmanager")


def _copy_if_needed(src: Path, dest: Path) -> bool:
    """Copy a file only when its size or mtime changed."""
    try:
        s = src.stat()
        d = dest.stat()
        if d.st_size == s.st_size and int(d.st_mtime) == int(s.st_mtime):
            return False
    except OSError:
        pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def _page_key(path: str) -> str:
    if path.endswith("/"):
        path += "index.html"
    return path.lstrip("/")


def _is_page(path: str) -> bool:
    return path.endswith((".html", ".htm"))


def _strip_query(url: str) -> str:
    return url.split("#", 1)[0].split("?", 1)[0]


class Rewriter:
    def __init__(self, site: Site, page_paths: set[str], asset_paths: set[str], lang: str):
        self.site = site
        self.page_paths = page_paths
        self.asset_paths = asset_paths
        self.lang = lang
        self.root_rel = site.root_path.strip("/")

    def _local(self, path: str) -> str | None:
        path = _page_key(path)
        if (self.lang == "ru" and path.endswith("/js/url.js")
                and path.startswith(self.root_rel + "/")):
            return "/ru/" + path
        prefix = self.root_rel + "/"
        if path.startswith(prefix):
            rel = path[len(prefix):]
            if rel in self.page_paths:
                base = "/ru/" if self.lang == "ru" else "/"
                return base + path
        if path in self.asset_paths:
            return "/" + path
        return None

    def rewrite(self, value: str, page_path: str) -> str:
        value = value.strip()
        if not value or is_skippable(value):
            return value
        absolute = urljoin(self.site.page_url(page_path), value)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            return value
        fragment = ""
        if "#" in value:
            fragment = "#" + value.split("#", 1)[1]
        if parsed.netloc != "www.honda.co.jp":
            return value
        local = self._local(parsed.path)
        if local is None:
            return "https://www.honda.co.jp" + parsed.path + fragment
        return local + fragment

    def rewrite_css(self, text: str, base_url: str) -> str:
        # Only inline style attributes / <style> blocks are handled here.
        import re
        def repl(m: re.Match) -> str:
            ref = m.group(2)
            if not ref or ref.startswith(("data:", "#")):
                return m.group(0)
            absolute = urljoin(base_url, ref)
            parsed = urlparse(absolute)
            if parsed.netloc != "www.honda.co.jp":
                return m.group(0)
            local = self._local(parsed.path)
            return f"url({m.group(1)}{local or ref}{m.group(1)})" if local else m.group(0)
        return re.sub(r"url\(\s*(['\"]?)(.*?)\1\s*\)", repl, text, flags=re.I | re.S)


def _cleanup(soup: BeautifulSoup, rewriter: Rewriter, page_path: str, lang: str) -> None:
    for tag in list(soup.find_all("script")):
        src = tag.get("src", "")
        if src.startswith(("http://", "https://", "//")) and "www.honda.co.jp" not in src:
            tag.decompose()
            continue
        if any(marker in src for marker in EXTERNAL_SCRIPTS):
            tag.decompose()

    for tag in list(soup.find_all("mf-search-box")):
        tag.decompose()

    for tag in list(soup.find_all("link")):
        href = tag.get("href", "")
        if href.startswith(("http://", "https://", "//")) and "www.honda.co.jp" not in href:
            tag.decompose()

    base = rewriter.site.page_url(page_path)
    for tag_name, attrs in URL_ATTRS.items():
        for tag in soup.find_all(tag_name):
            for attr in attrs:
                value = tag.get(attr)
                if value:
                    tag[attr] = rewriter.rewrite(value, page_path)
            srcset = tag.get("srcset")
            if srcset:
                parts = []
                for item in srcset.split(","):
                    item = item.strip()
                    if not item:
                        continue
                    bits = item.split()
                    bits[0] = rewriter.rewrite(bits[0], page_path)
                    parts.append(" ".join(bits))
                tag["srcset"] = ", ".join(parts)

    for tag in soup.find_all(style=True):
        tag["style"] = rewriter.rewrite_css(tag["style"], base)
    for tag in soup.find_all("style"):
        tag.string = rewriter.rewrite_css(tag.get_text(), base)

    if lang == "ru":
        html_tag = soup.find("html")
        if html_tag:
            html_tag["lang"] = "ru"


AGREEMENT_SCRIPT_VERSION = "webom-no-agreement-4"


def _bust_agreement_scripts(soup: BeautifulSoup) -> None:
    """Add a version query to the scripts that can show the agreement modal.

    This forces browsers that cached the old common.js/library.js to fetch the
    patched version after an update.  The query is ignored by the static file
    server.
    """
    for tag in soup.find_all("script", src=True):
        src = tag["src"]
        if not (src.endswith("/javascript/common.js") or src.endswith("/js/library.js")):
            continue
        if "v=" in src:
            continue
        tag["src"] = f"{src}?v={AGREEMENT_SCRIPT_VERSION}"


def _normalize_ru_text(soup: BeautifulSoup) -> None:
    """Replace leftover Japanese punctuation and the agreement placeholder."""
    for node in soup.find_all(string=True):
        if node.parent is not None and node.parent.name in ("script", "style"):
            continue
        value = str(node)
        new = value.replace("・", " · ").replace("、", ", ").replace("。", ". ")
        if new != value:
            node.replace_with(new)
    for tag in soup.find_all(attrs={"placeholder": True}):
        if tag.get("placeholder") == "同意書":
            tag["placeholder"] = "Согласие"


def _add_ru_banner(soup: BeautifulSoup, site: Site) -> None:
    if soup.body is None:
        return
    banner = BeautifulSoup(
        '<div class="webom-ru-banner" style="position:relative;z-index:9999;'
        'background:#fff8dc;color:#333;border-bottom:1px solid #e0c97f;'
        'padding:8px 12px;font:14px/1.4 sans-serif;text-align:center">'
        'Машинный перевод с японского. Возможны неточности — сверяйтесь с оригиналом. '
        f'<a href="/{site.root_path.lstrip("/")}" '
        'style="color:#005a9c">Открыть оригинал (日本語)</a></div>'
        '<style>.navCategory .listTitle::first-letter{text-transform:uppercase}</style>',
        "html.parser",
    )
    soup.body.insert(0, banner)


def _rewrite_js_menu(js: str, menu_html: str) -> str:
    from .translate import MENU_RE
    value = json.dumps(menu_html, ensure_ascii=False)
    js = MENU_RE.sub(lambda m: f"var MENU = {value};", js, count=1)
    # Old manuals build the agreement URL and device links from
    # BASE_DIRECTORY.  Keep them inside the translated tree.
    js = re.sub(
        r'var BASE_DIRECTORY = "/ownersmanual/([^"]+)";',
        r'var BASE_DIRECTORY = "/ru/ownersmanual/\1";',
        js,
        count=1,
    )
    return js


def _patch_ru_runtime(site_dir: Path, root_rel: str) -> None:
    """Teach new-style manuals that /ru/<manual>/ is also an index page.

    Every ``build`` copies the whole shared asset tree, so a later year's build
    can overwrite an earlier year's patched common.js.  Patch all years that
    have one, not just the year currently being built.
    """
    targets = {site_dir / root_rel / "javascript" / "common.js"}
    targets.update(site_dir.glob("ownersmanual/webom/jpn/*/*/javascript/common.js"))
    for common in sorted(targets):
        if common.exists():
            _patch_one_common(common)


def _patch_one_common(common: Path) -> None:
    text = common.read_text(encoding="utf-8", errors="replace")
    if "__webomRuPath" in text:
        return
    pattern = re.compile(
        r"(function is_index\(\)\s*\{\s*)"
        r"if \(location\.pathname == MANUAL_PATH"
    )
    replacement = (
        "\\1var __webomRuPath = \"/ru\" + MANUAL_PATH;\n"
        "  if (location.pathname == __webomRuPath || "
        "location.pathname == __webomRuPath + \"index.html\" || "
        "location.pathname == __webomRuPath + \"index2.html\") {\n"
        "    return true;\n"
        "  }\n"
        "  if (location.pathname == MANUAL_PATH"
    )
    patched, count = pattern.subn(replacement, text, count=1)
    if count:
        common.write_text(patched, encoding="utf-8")
        log.info("исправлен is_index для /ru: %s", common)


LEGACY_FONT_STACK = '"Segoe UI","Yu Gothic UI","Meiryo","Hiragino Sans",Arial,sans-serif'


def _fix_legacy_fonts(site_dir: Path) -> None:
    """Avoid the old MS-PGothic stack that looks monospaced in Windows Chrome.

    The 2017/2020/2023 manuals ask for Hiragino/Meiryo/MS-PGothic.  On a
    Windows machine without the first two, Chrome falls back to MS-PGothic,
    whose Latin glyphs look monospaced.  Use a proportional Windows-first stack
    for both the Japanese and Russian copies.
    """
    patterns = (
        "ownersmanual/webom/jpn/*/*/css/base.css",
        "ru/ownersmanual/webom/jpn/*/*/css/base.css",
    )
    for pattern in patterns:
        for path in sorted(site_dir.glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="replace")
            patched, count = re.subn(
                r"font-family:[^;]*MS-PGothic[^;]*;",
                f"font-family:{LEGACY_FONT_STACK};",
                text,
                count=1,
            )
            if count:
                path.write_text(patched, encoding="utf-8")
                log.info("исправлен шрифт для Windows: %s", path)


def _disable_agreement(site_dir: Path, root_rel: str) -> None:
    """Disable the "terms of use" modal in the offline copy.

    New manuals call ``agreement()`` from common.js; old manuals call
    ``Library.agreement.showAgreement()`` from library.js.  Both check a cookie
    before showing the modal, but a fresh browser profile always sees it.  For
    a personal offline copy there is no reason to ask again, so make the check
    unconditionally successful.  Patch all years because every build copies the
    shared asset tree again.
    """
    marker = "webom: agreement disabled"
    targets = set()
    targets.update(site_dir.glob("ownersmanual/webom/jpn/*/*/javascript/common.js"))
    targets.update(site_dir.glob("ownersmanual/webom/jpn/*/*/js/library.js"))
    targets.update(site_dir.glob("ru/ownersmanual/webom/jpn/*/*/javascript/common.js"))
    targets.update(site_dir.glob("ru/ownersmanual/webom/jpn/*/*/js/library.js"))
    for path in sorted(targets):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if marker in text:
            continue
        original = text
        # New-style manuals (2025/2026).
        text = re.sub(
            r"(function isAlreadyAgreed\(\)\s*\{\s*)",
            r"\1\n    return true; // " + marker + "\n",
            text,
            count=1,
        )
        text = re.sub(
            r"(function agreement\(\)\s*\{\s*)",
            r"\1\n  return; // " + marker + "\n",
            text,
            count=1,
        )
        # Old-style manuals (2017/2020/2023).
        text = re.sub(
            r"(isAlreadyAgreed:\s*function\s*\([^)]*\)\s*\{\s*)",
            r"\1\n                    return true; // " + marker + "\n",
            text,
            count=1,
        )
        text = re.sub(
            r"(showAgreement:\s*function\s*\([^)]*\)\s*\{\s*)",
            r"\1\n                    return; // " + marker + "\n",
            text,
            count=1,
        )
        if text != original:
            path.write_text(text, encoding="utf-8")
            log.info("окно соглашения отключено: %s", path)


def _localize_new_common(site_dir: Path) -> None:
    """Translate a few visible strings generated by new-style common.js."""
    marker = "webom: localized common"
    targets = set()
    targets.update(site_dir.glob("ownersmanual/webom/jpn/*/*/javascript/common.js"))
    targets.update(site_dir.glob("ru/ownersmanual/webom/jpn/*/*/javascript/common.js"))
    replacements = (
        ('myTitle = "画像から探す" + bread;',
         'myTitle = (location.pathname.indexOf("/ru/") === 0 ? "Поиск по изображению" : "画像から探す") + bread;'),
        ('myTitle = "一覧目次" + bread;',
         'myTitle = (location.pathname.indexOf("/ru/") === 0 ? "Содержание" : "一覧目次") + bread;'),
        ('myTitle = "警告灯/表示灯一覧" + bread;',
         'myTitle = (location.pathname.indexOf("/ru/") === 0 ? "Список сигнальных и индикаторных ламп" : "警告灯/表示灯一覧") + bread;'),
        ('>取扱説明書トップ</a>',
         """>' + (location.pathname.indexOf("/ru/") === 0 ? "Главная страница руководства" : "取扱説明書トップ") + '</a>"""),
        ('placeholder="取扱説明書内を検索"',
         r'''placeholder="' + (location.pathname.indexOf("/ru/") === 0 ? "Поиск по руководству" : "取扱説明書内を検索") + '"'''),
        ('  const form = document.querySelector(".mf_finder_searchBox_form");\n  const hiddenInput = document.createElement("input");',
         '  const form = document.querySelector(".mf_finder_searchBox_form");\n  if (!form) return;\n  const hiddenInput = document.createElement("input");'),
        ('function setMarsSearch() {\n  let el = document.createElement("script");',
         'function setMarsSearch() {\n  return; // webom: external search disabled offline\n  let el = document.createElement("script");'),
    )
    for path in sorted(targets):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        original = text
        for old, new in replacements:
            if old in text:
                text = text.replace(old, new, 1)
        if marker not in text:
            text = text.replace("function setTitle() {", "function setTitle() { // " + marker, 1)
        if text != original:
            path.write_text(text, encoding="utf-8")
            log.info("локализован common.js: %s", path)


def _localize_bookmark_bubble(site_dir: Path) -> None:
    """Translate the PWA install bubble shown by bookmark_bubble.js."""
    old = r"""bubbleInner.innerHTML = 'このWebアプリをインストールしましょう。矢印をタップして<b>\'ホーム画面に追加\'<b>';"""
    new = r"""bubbleInner.innerHTML = (location.pathname.indexOf("/ru/") === 0 ? 'Установите это веб-приложение. Нажмите на стрелку, чтобы <b>\'Добавить на главный экран\'<b>' : 'このWebアプリをインストールしましょう。矢印をタップして<b>\'ホーム画面に追加\'<b>');"""
    targets = set()
    targets.update(site_dir.glob("ownersmanual/webom/jpn/*/*/asset/js/bookmark_bubble.js"))
    targets.update(site_dir.glob("ru/ownersmanual/webom/jpn/*/*/asset/js/bookmark_bubble.js"))
    for path in sorted(targets):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "Установите это веб-приложение" in text or old not in text:
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        log.info("локализован bookmark_bubble.js: %s", path)


def _copy_translated_data(site_dir: Path, root_rel: str, translated_dir: Path) -> None:
    """Overwrite shared Japanese data with translated tooltip data."""
    rels = (
        "language/ja_JP/main/json/visualindex_content.json",
        "language/ja_JP/main/json/inline.json",
        "pc/js/data/appearance.point.js",
        "pc/js/data/interior.point.js",
    )
    for rel in rels:
        src = translated_dir / rel
        if not src.is_file():
            continue
        dest = site_dir / "ru" / root_rel / rel
        _copy_if_needed(src, dest)


def _rewrite_ru_data_scripts(soup: BeautifulSoup, site_dir: Path, root_rel: str,
                             translated_dir: Path) -> None:
    """Point old tooltip data scripts at their translated Russian copies."""
    for tag in soup.find_all("script", src=True):
        src = tag["src"]
        for name in ("appearance.point.js", "interior.point.js"):
            marker = "/pc/js/data/" + name
            if not src.endswith(marker):
                continue
            if (translated_dir / "pc/js/data" / name).is_file():
                if src.startswith("/ownersmanual/"):
                    tag["src"] = "/ru" + src
                elif src.startswith("https://www.honda.co.jp/ownersmanual/"):
                    tag["src"] = "/ru" + src[len("https://www.honda.co.jp"):]
            break


def _ensure_legacy_aliases(site_dir: Path, root_rel: str) -> None:
    """Fill a couple of paths that the original Honda pages reference but 404.

    The new manuals use ``asset/images/point_*.png`` in their own markup, while
    ``language/ja_JP/main/index.html`` still asks for
    ``images/common/point_*.png``.  The original site returns 404 for the
    latter; keep the local copy free of that noise by aliasing the existing
    files.
    """
    root = site_dir / root_rel
    aliases = {
        "images/common/point_off.png": "asset/images/point_off.png",
        "images/common/point_on.png": "asset/images/point_on.png",
    }
    for dest_rel, src_rel in aliases.items():
        dest = root / dest_rel
        src = root / src_rel
        if not dest.exists() and src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            log.info("локальный алиас: %s -> %s", dest_rel, src_rel)


def _mirror_shared_assets(site_dir: Path, root_rel: str) -> None:
    """Copy small shared directories into the Russian tree.

    Most links in the HTML point to the Japanese tree explicitly, but some
    scripts build relative URLs (``../asset/...``, ``images/...``) from the
    current page.  Mirroring the small shared directories makes those URLs work
    without duplicating the large ``img/`` photo collection.
    """
    src_root = site_dir / root_rel
    dst_root = site_dir / "ru" / root_rel
    rel_dirs = ("asset", "images", "css", "javascript", "js", "pc/js", "details/js")
    copied = 0
    for rel in rel_dirs:
        src = src_root / rel
        if not src.is_dir():
            continue
        for item in src.rglob("*"):
            if not item.is_file():
                continue
            # The Russian menu is generated separately and must not be
            # overwritten by the Japanese url.js.
            if rel == "js" and item.name == "url.js":
                continue
            dest = dst_root / item.relative_to(src_root)
            if _copy_if_needed(item, dest):
                copied += 1
    # Images referenced from JS/JSON are normally loaded through a relative
    # path such as ../img/foo.png.  Copy just those files; the bulk of img/ is
    # already referenced by absolute URLs in the HTML and does not need a
    # second copy.
    img_ref = re.compile(r"(?:\.\./)+img/([A-Za-z0-9_@%+=,~./-]+)")
    for code in list(src_root.rglob("*.js")) + list(src_root.rglob("*.json")):
        if not code.is_file():
            continue
        try:
            text = code.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in img_ref.finditer(text):
            rel = "img/" + match.group(1).split("?", 1)[0].split("#", 1)[0]
            src = src_root / rel
            if not src.is_file():
                continue
            dest = dst_root / rel
            if _copy_if_needed(src, dest):
                copied += 1

    # Data loaded by visual.js and other scripts lives under language/.
    # Copy only JSON files: the translated HTML in that directory must win.
    lang_src = src_root / "language"
    if lang_src.is_dir():
        for item in lang_src.rglob("*.json"):
            if not item.is_file():
                continue
            dest = dst_root / item.relative_to(src_root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(item, dest)
                copied += 1

    for name in ("webclip.png", "favicon.ico"):
        src = src_root / name
        if src.is_file():
            dest = dst_root / name
            if _copy_if_needed(src, dest):
                copied += 1
    if copied:
        log.info("зеркалировано общих файлов в /ru: %d", copied)


def build_year(site: Site, paths: Paths, target: str = "ru") -> dict:
    manifest = load_manifest(paths, site)
    raw_dir = year_dir(paths, site, "raw")
    translated_dir = paths.translated / target / site.car / site.year
    site_dir = paths.site

    page_paths = {_page_key(p["path"]) for p in manifest["pages"] if p.get("status") != "error"}
    root_rel = site.root_path.strip("/")

    # Copy assets into the site root, preserving URL paths.
    host_dir = paths.assets / "www.honda.co.jp"
    asset_paths: set[str] = set()
    copied = 0
    if host_dir.exists():
        for src in host_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(host_dir)
            dest = site_dir / rel
            if _copy_if_needed(src, dest):
                copied += 1
            asset_paths.add(rel.as_posix())
    log.info("скопировано ассетов: %d", copied)
    _patch_ru_runtime(site_dir, root_rel)
    _localize_new_common(site_dir)
    _localize_bookmark_bubble(site_dir)
    _disable_agreement(site_dir, root_rel)
    _ensure_legacy_aliases(site_dir, root_rel)
    for alias in ("images/common/point_off.png", "images/common/point_on.png"):
        alias_path = site_dir / root_rel / alias
        if alias_path.is_file():
            asset_paths.add(f"{root_rel}/{alias}")

    stats = {"ja": 0, "ru": 0, "ru_fallback": 0}

    # Japanese original
    rewriter_ja = Rewriter(site, page_paths, asset_paths, "ja")
    for page in manifest["pages"]:
        if page.get("status") == "error":
            continue
        html = (raw_dir / page["path"]).read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        _cleanup(soup, rewriter_ja, page["path"], "ja")
        _bust_agreement_scripts(soup)
        dest = site_dir / root_rel / page["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        output = str(soup)
        if page["path"] == "agreement.html" and soup.body is not None:
            output = soup.body.decode_contents()
        dest.write_text(output, encoding="utf-8")
        stats["ja"] += 1

    # Russian translation
    rewriter_ru = Rewriter(site, page_paths, asset_paths, "ru")
    for page in manifest["pages"]:
        if page.get("status") == "error":
            continue
        src = translated_dir / page["path"]
        fallback = not src.exists()
        if fallback:
            src = raw_dir / page["path"]
            stats["ru_fallback"] += 1
        html = src.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        _cleanup(soup, rewriter_ru, page["path"], "ru")
        _rewrite_ru_data_scripts(soup, site_dir, root_rel, translated_dir)
        _bust_agreement_scripts(soup)
        _normalize_ru_text(soup)
        if page["path"] != "agreement.html":
            _add_ru_banner(soup, site)
        if fallback:
            notice = BeautifulSoup(
                '<div style="background:#fdd;padding:8px;text-align:center;'
                'font:14px sans-serif">Перевод этой страницы ещё не готов — показан оригинал.</div>',
                "html.parser",
            )
            soup.body.insert(1, notice)
        dest = site_dir / "ru" / root_rel / page["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        output = str(soup)
        if page["path"] == "agreement.html" and soup.body is not None:
            output = soup.body.decode_contents()
        dest.write_text(output, encoding="utf-8")
        stats["ru"] += 1

    # RU-specific url.js with translated menu.
    from .assets import asset_file
    menu_src = translated_dir / "menu.html"
    raw_js = asset_file(paths, site, "js/url.js")
    if menu_src.exists() and raw_js.exists():
        js = raw_js.read_text(encoding="utf-8", errors="replace")
        menu_html = menu_src.read_text(encoding="utf-8")
        js = _rewrite_js_menu(js, menu_html)
        dest = site_dir / "ru" / root_rel / "js" / "url.js"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(js, encoding="utf-8")
        log.info("меню переведено: %s", dest)

    _mirror_shared_assets(site_dir, root_rel)
    _copy_translated_data(site_dir, root_rel, translated_dir)
    _fix_legacy_fonts(site_dir)

    # JSON databases used by the JS-generated side menu (new-style manuals).
    for rel in manifest.get("data_files", []):
        src = raw_dir / rel
        if not src.exists():
            continue
        ja_data = _filter_menu_db(src, page_paths, rel)
        if ja_data is None:
            continue
        dest = site_dir / root_rel / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(ja_data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        translated = translated_dir / rel
        if translated.exists():
            ru_data = _filter_menu_db(translated, page_paths, rel) or ja_data
            filled = _fill_ru_search_text(ru_data, translated_dir)
            if filled:
                log.info("поисковый текст из русских страниц: %s (%d записей)", rel, filled)
            dest_ru = site_dir / "ru" / root_rel / rel
            dest_ru.parent.mkdir(parents=True, exist_ok=True)
            dest_ru.write_text(json.dumps(ru_data, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        log.info("меню JSON: %s", rel)

    _build_index(paths, site_dir)
    return stats


def _ru_page_text(translated_dir: Path, template: str) -> str | None:
    """Extract visible Russian text from the translated page for an entry."""
    if not template:
        return None
    name = template.rsplit("/", 1)[-1].split("?", 1)[0].split("#", 1)[0]
    if not name:
        return None
    candidates = (
        translated_dir / "details" / name,
        translated_dir / "detailsnavi" / name,
    )
    page = next((p for p in candidates if p.is_file()), None)
    if page is None:
        return None
    soup = BeautifulSoup(page.read_text(encoding="utf-8", errors="replace"), "lxml")
    for tag in soup.find_all(["script", "style", "noscript", "template", "header", "footer", "nav", "aside"]):
        tag.decompose()
    for selector in (".webom-ru-banner", ".layout-header", ".layout-footer", ".nav-side"):
        for tag in soup.select(selector):
            tag.decompose()
    main = soup.select_one("div.main") or soup.select_one("main") or soup.body
    if main is None:
        return None
    text = re.sub(r"\s+", " ", main.get_text(" ", strip=True)).strip()
    return text or None


def _fill_ru_search_text(data: dict, translated_dir: Path) -> int:
    """Replace Japanese contentsDB.text with text from the translated page."""
    filled = 0
    for entry in data.get("ContentsList", []):
        if not isinstance(entry, dict):
            continue
        text = _ru_page_text(translated_dir, entry.get("HTMLtemplate", ""))
        if text:
            entry["text"] = text
            filled += 1
    return filled


def _filter_menu_db(path: Path, page_paths: set[str], rel: str) -> dict | None:
    """Drop menu entries whose target page is not part of the local copy."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    entries = data.get("ContentsList") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return data
    subdir = "detailsnavi" if "/navi/" in rel else "details"
    kept = []
    for entry in entries:
        template = entry.get("HTMLtemplate") or ""
        name = template.rsplit("/", 1)[-1]
        if not name or _page_key(f"{subdir}/{name}") in page_paths:
            kept.append(entry)
    data["ContentsList"] = kept
    return data


def _build_index(paths: Paths, site_dir: Path) -> None:
    years: dict[str, list[str]] = {}
    for manifest_file in sorted(paths.manifests.glob("*.json")):
        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        car = data.get("site", {}).get("car")
        year = data.get("site", {}).get("year")
        if not car or not year:
            continue
        years.setdefault(car, []).append(year)

    rows = []
    for car in sorted(years):
        for year in sorted(set(years[car]), reverse=True):
            root = f"ownersmanual/webom/jpn/{car}/{year}/"
            if (site_dir / root / "index.html").exists():
                ru = f"ru/{root}index.html"
                rows.append(
                    f'<tr><td><b>{car.upper()}</b> {year}</td>'
                    f'<td><a href="/{root}">日本語 (оригинал)</a></td>'
                    f'<td><a href="/{ru}">Русский (перевод)</a></td></tr>'
                )
    html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Honda — руководства пользователя (локальная копия)</title>
<style>html{{height:100%}}
body{{font:16px/1.5 sans-serif;min-height:100vh;margin:0;padding:0;
  box-sizing:border-box;display:flex;flex-direction:column}}
main{{flex:1 0 auto;width:100%;max-width:900px;margin:0 auto;padding:40px 16px 0;box-sizing:border-box}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:10px;text-align:left}}
a{{color:#005a9c}}
.site-footer{{width:100%;margin:0;background:#333;color:#eee;padding:6px 16px 8px;
  border-radius:18px 18px 0 0;box-sizing:border-box;text-align:center;font-size:13px;line-height:1.2}}
.site-footer a{{color:#9ccfff;text-decoration:none}}
.site-footer a:hover{{text-decoration:underline}}
.footer-line{{display:flex;justify-content:center;align-items:center;flex-wrap:nowrap;
  gap:0 8px;white-space:nowrap}}
.footer-sep{{color:#888}}
.footer-icon{{display:inline-block;width:1.2em;text-align:center;margin-right:3px}}</style></head>
<body><main><h1>Honda — руководства пользователя</h1>
<p>Локальная копия. Русская версия — машинный перевод, оригинал сохранён рядом.</p>
<table><thead><tr><th>Модель / год</th><th>Оригинал</th><th>Перевод</th></tr></thead>
<tbody>{''.join(rows) or '<tr><td colspan=3>Пока ничего не собрано.</td></tr>'}</tbody></table>
</main>
<footer class="site-footer">
  <div class="footer-line">
    <span>Выкачано, собрано и переведено:</span>
    <a href="https://t.me/artamonov_av" target="_blank" rel="noopener"><span class="footer-icon">✈</span>https://t.me/artamonov_av</a>
    <span class="footer-sep">|</span>
    <a href="mailto:anatoly@rtamonov.ru"><span class="footer-icon">✉</span>anatoly@rtamonov.ru</a>
  </div>
</footer>
</body></html>"""
    (site_dir / "index.html").write_text(html, encoding="utf-8")
