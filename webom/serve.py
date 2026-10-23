from __future__ import annotations

import argparse
import os
import posixpath
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

_ROUTE_RE = re.compile(r"^(/ru)?(/ownersmanual/webom/jpn/([^/]+)/)(.*)$")
_YEAR_RE = re.compile(r"^(\d{4})(?:/|$)")
_CACHE_TEXT_EXT = {".html", ".htm", ".js", ".mjs", ".json", ".css", ".xml", ".txt"}
_CACHE_MEDIA_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".svgz", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp4", ".webm", ".mp3",
    ".wav", ".ogg", ".pdf",
}


class FallbackRequestHandler(SimpleHTTPRequestHandler):
    """Static handler for the offline copy with a small URL fallback.

    The translated pages live under ``/ru/...`` while most images, scripts and
    JSON databases are shared with the Japanese copy under ``/ownersmanual/...``.
    A few old/new Honda scripts build relative URLs from the page location, so
    the browser can ask for a path that does not exist under ``/ru``.  Before
    returning 404, try the same path without ``/ru`` and, when the year segment
    is missing, try the year inferred from the Referer header (or any available
    year).
    """

    def __init__(self, *args, directory: str | None = None, **kwargs):
        # BaseHTTPRequestHandler processes the request from __init__, so this
        # must be initialised before calling super().
        self._years_cache: dict[str, list[str]] = {}
        super().__init__(*args, directory=directory, **kwargs)

    def _years(self, car: str) -> list[str]:
        if car in self._years_cache:
            return self._years_cache[car]
        root = Path(self.directory) / "ownersmanual" / "webom" / "jpn" / car
        years = sorted(
            (p.name for p in root.iterdir() if p.is_dir() and p.name.isdigit()),
            reverse=True,
        ) if root.is_dir() else []
        self._years_cache[car] = years
        return years

    def _referer_year(self, car: str) -> str | None:
        referer = self.headers.get("Referer", "")
        if not referer:
            return None
        path = urlsplit(referer).path
        m = re.search(rf"/{re.escape(car)}/(\d{{4}})(?:/|$)", path)
        return m.group(1) if m else None

    def _exists(self, path: str) -> bool:
        fs_path = self.translate_path(path)
        if path.endswith("/"):
            return os.path.isfile(os.path.join(fs_path, "index.html"))
        return os.path.isfile(fs_path)

    def _fallback_path(self, raw_path: str) -> str | None:
        path = unquote(urlsplit(raw_path).path)
        if self._exists(path):
            return None

        m = _ROUTE_RE.match(path)
        if not m:
            return None

        ru_prefix, prefix, car, rest = m.groups()
        prefixes = [prefix]
        if ru_prefix:
            prefixes.append(prefix[3:])  # /ru/ownersmanual/... -> /ownersmanual/...
        else:
            prefixes.append("/ru" + prefix)

        candidates: list[str] = []
        year = self._referer_year(car)
        years = [year] if year else []
        years += [y for y in self._years(car) if y != year]

        for base in prefixes:
            candidates.append(base + rest)
            head = rest.split("/", 1)[0]
            if not _YEAR_RE.match(rest):
                for y in years:
                    candidates.append(base + y + "/" + rest.lstrip("/"))

        seen: set[str] = set()
        for candidate in candidates:
            candidate = posixpath.normpath(candidate)
            if not candidate.startswith("/"):
                candidate = "/" + candidate
            if candidate in seen:
                continue
            seen.add(candidate)
            if self._exists(candidate + "/" if candidate.endswith("/") else candidate):
                return quote(candidate, safe="/")
        return None

    def send_response(self, code, message=None):
        self._webom_status = code
        super().send_response(code, message)

    def end_headers(self):
        code = getattr(self, "_webom_status", 200)
        path = unquote(urlsplit(self.path).path).lower()
        ext = os.path.splitext(path)[1]
        if code == 200:
            if ext in _CACHE_TEXT_EXT:
                self.send_header("Cache-Control", "no-cache")
            elif ext in _CACHE_MEDIA_EXT:
                self.send_header("Cache-Control", "public, max-age=86400")
            else:
                self.send_header("Cache-Control", "no-cache")
        elif code == 304:
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        fallback = self._fallback_path(self.path)
        if fallback is not None:
            self.path = fallback
        return super().send_head()


def run_server(site_dir: Path, host: str = "127.0.0.1", port: int = 8000) -> None:
    import functools

    handler = functools.partial(FallbackRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"http://{host}:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the offline Honda manual copy")
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parent.parent / "site")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if not (args.site / "index.html").exists():
        print(f"site/index.html not found: {args.site}", file=sys.stderr)
        return 1
    run_server(args.site, args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
