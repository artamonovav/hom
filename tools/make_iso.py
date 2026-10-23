#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent

GROUPS = (
    ("Honda Freed 2 Owners Manual.iso", ("2017", "2020", "2023"), "FREED2_MANUAL",
     "Honda Freed 2 Owners Manual"),
    ("Honda Freed 3 Owners Manual.iso", ("2025", "2026"), "FREED3_MANUAL",
     "Honda Freed 3 Owners Manual"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prune_site(site: Path, years: tuple[str, ...]) -> None:
    selected = set(years)
    roots = (
        site / "ownersmanual" / "webom" / "jpn",
        site / "ru" / "ownersmanual" / "webom" / "jpn",
    )
    for root in roots:
        if not root.is_dir():
            continue
        for car_dir in root.iterdir():
            if not car_dir.is_dir():
                continue
            for year_dir in list(car_dir.iterdir()):
                if year_dir.is_dir() and year_dir.name.isdigit() and year_dir.name not in selected:
                    shutil.rmtree(year_dir)


def _filter_index(site: Path, years: tuple[str, ...]) -> None:
    index = site / "index.html"
    soup = BeautifulSoup(index.read_text(encoding="utf-8"), "lxml")
    tbody = soup.select_one("table tbody")
    if tbody is None:
        raise RuntimeError("site/index.html: table tbody not found")
    selected = set(years)
    for row in list(tbody.find_all("tr")):
        text = row.get_text(" ", strip=True)
        match = re.search(r"\b(20\d{2})\b", text)
        if not match or match.group(1) not in selected:
            row.decompose()
    index.write_text(str(soup), encoding="utf-8")


def _write_readme(stage: Path, years: tuple[str, ...]) -> None:
    template = (ROOT / "packaging" / "README.txt").read_text(encoding="utf-8")
    urls = "\n".join(
        f"https://www.honda.co.jp/ownersmanual/webom/jpn/freed/{year}/"
        for year in years
    )
    text = template.replace("{{YEARS}}", ", ".join(years)).replace("{{SOURCE_URLS}}", urls)
    (stage / "README.txt").write_text(text, encoding="utf-8")


def _write_autorun(stage: Path, label: str) -> None:
    template = (ROOT / "packaging" / "autorun.inf").read_text(encoding="utf-8")
    text = template.replace("{{LABEL}}", label)
    data = text.replace("\r\n", "\n").replace("\n", "\r\n")
    (stage / "autorun.inf").write_bytes(data.encode("ascii"))


def _stage(stage: Path, site: Path, years: tuple[str, ...], label: str) -> None:
    shutil.copytree(site, stage / "site")
    _prune_site(stage / "site", years)
    _filter_index(stage / "site", years)
    shutil.copy2(ROOT / "serve-freed.ps1", stage / "serve-freed.ps1")
    shutil.copy2(ROOT / "packaging" / "start.cmd", stage / "start.cmd")
    shutil.copy2(ROOT / "packaging" / "start-linux.sh", stage / "start-linux.sh")
    _write_readme(stage, years)
    _write_autorun(stage, label)
    cmd = stage / "start.cmd"
    data = cmd.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    cmd.write_bytes(data)
    (stage / "start-linux.sh").chmod(0o755)


def _build_group(output: Path, site: Path, years: tuple[str, ...], label: str, volume: str) -> None:
    tmp_iso = output.with_name(output.name + ".tmp")
    try:
        with tempfile.TemporaryDirectory(prefix="freed-iso-") as tmp:
            stage = Path(tmp)
            _stage(stage, site, years, label)
            subprocess.run(
                [
                    "genisoimage", "-quiet", "-J", "-joliet-long", "-R",
                    "-V", volume, "-o", str(tmp_iso), str(stage),
                ],
                check=True,
            )
        os.replace(tmp_iso, output)
    except Exception:
        try:
            tmp_iso.unlink()
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the split Freed manual ISOs")
    parser.add_argument("--site", type=Path, default=ROOT / "site")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build")
    args = parser.parse_args(argv)

    site = args.site.resolve()
    if not (site / "index.html").is_file():
        print(f"site/index.html not found: {site}", file=sys.stderr)
        return 1
    if not shutil.which("genisoimage"):
        print("genisoimage not found (install genisoimage/xorriso)", file=sys.stderr)
        return 1

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    legacy = output_dir / "freed-manual.iso"
    if legacy.exists():
        legacy.unlink()

    for filename, years, volume, label in GROUPS:
        output = output_dir / filename
        _build_group(output, site, years, label, volume)
        size = output.stat().st_size
        print(f"ISO: {output}")
        print(f"  years: {', '.join(years)}")
        print(f"  size: {size / 1024 / 1024:.0f} MiB")
        print(f"  SHA-256: {sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
