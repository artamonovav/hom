from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BASE_URL = "https://www.honda.co.jp"
PROJECT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Site:
    car: str = "freed"
    year: str = "2020"
    base: str = BASE_URL

    @property
    def root_path(self) -> str:
        return f"/ownersmanual/webom/jpn/{self.car}/{self.year}/"

    @property
    def root_url(self) -> str:
        return self.base + self.root_path

    @property
    def year_index_url(self) -> str:
        return f"{self.base}/ownersmanual/webom/jpn/{self.car}/"

    def in_scope(self, url: str) -> bool:
        return url == self.root_url or url.startswith(self.root_url)

    def rel_path(self, url: str) -> str:
        """Path of a page relative to the year root ('index.html' for the root)."""
        if not url.startswith(self.root_url):
            raise ValueError(f"URL outside scope: {url}")
        rel = url[len(self.root_url):]
        rel = rel.split("#", 1)[0].split("?", 1)[0]
        if rel == "" or rel.endswith("/"):
            rel += "index.html"
        return rel

    def page_url(self, path: str) -> str:
        return self.root_url + path


@dataclass(frozen=True)
class Paths:
    data: Path
    site: Path

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def assets(self) -> Path:
        return self.data / "assets"

    @property
    def translated(self) -> Path:
        return self.data / "translated"

    @property
    def manifests(self) -> Path:
        return self.data / "manifests"

    @property
    def reports(self) -> Path:
        return self.data / "reports"

    @property
    def db(self) -> Path:
        return self.data / "translate.sqlite"

    def ensure(self) -> None:
        for p in (self.data, self.site, self.raw, self.assets,
                  self.translated, self.manifests, self.reports):
            p.mkdir(parents=True, exist_ok=True)


def year_dir(paths: Paths, site: Site, kind: str) -> Path:
    return getattr(paths, kind) / site.car / site.year
