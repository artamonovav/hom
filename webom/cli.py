from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .assets import download_assets
from .build import build_year
from .config import PROJECT_DIR, Paths, Site
from .crawl import crawl, discover_years, load_manifest
from .net import Fetcher
from .translate import translate_year

log = logging.getLogger("webom")


def _setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--car", default="freed")
    p.add_argument("--year", default="2020")
    p.add_argument("--base", default="https://www.honda.co.jp")
    p.add_argument("--data", type=Path, default=PROJECT_DIR / "data")
    p.add_argument("--site", dest="site_dir", type=Path, default=PROJECT_DIR / "site")


def _site(args) -> tuple[Site, Paths]:
    site = Site(car=args.car, year=args.year, base=args.base)
    paths = Paths(data=args.data, site=args.site_dir)
    paths.ensure()
    return site, paths


def cmd_crawl(args) -> int:
    site, paths = _site(args)
    fetcher = Fetcher(min_interval=args.interval)
    manifest = crawl(site, paths, fetcher=fetcher, max_pages=args.max_pages, force=args.force)
    if not args.no_assets:
        download_assets(site, paths, fetcher=Fetcher(min_interval=min(args.interval, 0.15)))
    print(f"Страниц: {len(manifest['pages'])}")
    return 0


def cmd_assets(args) -> int:
    site, paths = _site(args)
    download_assets(site, paths, fetcher=Fetcher(min_interval=args.interval))
    return 0


def cmd_translate(args) -> int:
    site, paths = _site(args)
    report = translate_year(
        site, paths, provider_name=args.provider, target=args.target,
        limit=args.limit, src=args.source_lang,
    )
    print(json.dumps({k: v for k, v in report.items() if k != "site"},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_build(args) -> int:
    site, paths = _site(args)
    stats = build_year(site, paths, target=args.target)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


def cmd_all(args) -> int:
    cmd_crawl(args)
    return cmd_translate(args) or cmd_build(args)


def cmd_years(args) -> int:
    site = Site(car=args.car, year=args.year, base=args.base)
    years = discover_years(site, Fetcher())
    print("\n".join(years))
    return 0


def cmd_status(args) -> int:
    site, paths = _site(args)
    try:
        manifest = load_manifest(paths, site)
    except SystemExit as exc:
        print(exc)
        return 1
    pages = [p for p in manifest["pages"] if p.get("status") != "error"]
    translated_dir = paths.translated / args.target / site.car / site.year
    done = sum(1 for p in pages if (translated_dir / p["path"]).exists())
    raw_size = sum((paths.raw / site.car / site.year / p["path"]).stat().st_size
                   for p in pages if (paths.raw / site.car / site.year / p["path"]).exists())
    report_path = paths.reports / f"translation-{site.car}-{site.year}-{args.target}.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    print(f"Страниц в манифесте : {len(pages)}")
    print(f"Сырой HTML          : {raw_size / 1024 / 1024:.1f} МиБ")
    print(f"Переведено страниц  : {done}")
    if report:
        print(f"Уникальных блоков   : {report.get('unique_sources')}")
        print(f"Знаков (уникальных) : {report.get('source_chars')}")
        print(f"Пропущено блоков    : {report.get('missing')}")
    from .translate import load_overrides, open_db
    overrides = load_overrides(open_db(paths), args.target)
    print(f"DeepL overrides     : {len(overrides)}")
    return 0


def _freq_years(args, paths) -> list[str]:
    if args.years:
        return [y.strip() for y in args.years.split(",") if y.strip()]
    from .freq import manifest_years
    return manifest_years(paths, args.car)


def cmd_freq(args) -> int:
    import csv
    from . import freq

    _, paths = _site(args)
    years = _freq_years(args, paths)
    data = None if args.refresh else freq.load_frequencies(paths, args.car)
    if data is None or set(data.get("years", [])) != set(years):
        data = freq.collect_frequencies(paths, args.car, years)
        path = freq.save_frequencies(paths, args.car, data)
        log.info("частотность сохранена: %s", path)

    rows = freq.select(data["rows"], min_count=args.min_count,
                       min_chars=args.min_chars, content_only=args.content)
    shown = rows[:args.top]
    print(f"{'#':>4} {'раз':>5} {'стр':>4} {'знак':>6}  фраза")
    for i, row in enumerate(shown, 1):
        text = row["text"].replace("\n", " ")
        if len(text) > 84:
            text = text[:81] + "..."
        print(f"{i:4d} {row['count']:5d} {row['pages']:4d} {row['text_chars']:6d}  {text}")
    text_total = data.get("text_chars") or sum(
        row["text_chars"] for row in data["rows"].values())
    print(f"\nуникальных: {data['unique']}, вхождений: {data['occurrences']}, "
          f"знаков текста: {text_total}, с разметкой: {data['chars']}")

    if args.budget:
        stops = [100, 250, 500, 1000, 2000, 3000, 5000]
        print("\n  топ  знаков   вхождений")
        for item in freq.cumulative(rows, stops):
            print(f"{item['rank']:6d} {item['chars']:8d} {item['occurrences']:10d}")

    if args.csv:
        path = Path(args.csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(["rank", "count", "pages", "text_chars", "chars", "kind", "text", "html"])
            for i, row in enumerate(rows, 1):
                writer.writerow([i, row["count"], row["pages"], row["text_chars"],
                                 row["chars"], row["kind"], row["text"], row["html"]])
        print(f"CSV: {path}")
    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"JSON: {path}")
    return 0


def cmd_deepl(args) -> int:
    from .deepl import salvage_failed, translate_menus, translate_top

    _, paths = _site(args)
    years = _freq_years(args, paths)
    budget = args.budget
    if budget != "auto":
        try:
            budget = int(budget)
        except ValueError:
            print("--budget: нужно целое число или auto", file=sys.stderr)
            return 2
    if args.salvage:
        result = salvage_failed(paths, args.car, years, budget=budget,
                                min_chars=args.salvage_min_chars,
                                max_tags=args.salvage_max_tags,
                                dry_run=args.dry_run)
    elif args.menus:
        result = translate_menus(paths, args.car, years, budget=budget,
                                 dry_run=args.dry_run,
                                 retry_failed=args.retry_failed)
    else:
        result = translate_top(
            paths, args.car, years, budget=budget,
            min_count=args.min_count, min_chars=args.min_chars, top=args.top,
            content_only=not args.all, dry_run=args.dry_run, refresh=args.refresh,
            retry_failed=args.retry_failed,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    from .deepl import deepl_usage
    usage = deepl_usage()
    if usage:
        print(f"DeepL: использовано {usage['character_count']} из "
              f"{usage['character_limit']}, осталось "
              f"{usage['character_limit'] - usage['character_count']}")
    if not args.dry_run and result["translated"]:
        print("Примените переводы: webom translate + webom build для каждого года",
              file=sys.stderr)
    return 0


def cmd_verify(args) -> int:
    from .verify import print_result, verify_site

    _, paths = _site(args)
    result = verify_site(paths, args.car)
    return print_result(result)


def cmd_serve(args) -> int:
    from .serve import run_server

    root = args.site_dir
    if not (root / "index.html").exists():
        print(f"Нет {root}/index.html — сначала build", file=sys.stderr)
        return 1
    run_server(root, args.host, args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webom",
        description="Локальная копия и перевод руководств Honda (webom).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("crawl", help="обойти страницы и скачать ресурсы")
    _add_common(p)
    p.add_argument("--max-pages", type=int, default=None)
    p.add_argument("--interval", type=float, default=0.35)
    p.add_argument("--force", action="store_true", help="перекачать существующие страницы")
    p.add_argument("--no-assets", action="store_true")
    p.set_defaults(func=cmd_crawl)

    p = sub.add_parser("assets", help="только скачать ресурсы")
    _add_common(p)
    p.add_argument("--interval", type=float, default=0.15)
    p.set_defaults(func=cmd_assets)

    p = sub.add_parser("translate", help="перевести страницы")
    _add_common(p)
    p.add_argument("--provider", default="google-web")
    p.add_argument("--target", default="ru")
    p.add_argument("--source-lang", default="ja")
    p.add_argument("--limit", type=int, default=None, help="только первые N страниц (для теста)")
    p.set_defaults(func=cmd_translate)

    p = sub.add_parser("build", help="собрать офлайн-сайт")
    _add_common(p)
    p.add_argument("--target", default="ru")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("all", help="crawl + translate + build")
    _add_common(p)
    p.add_argument("--provider", default="google-web")
    p.add_argument("--target", default="ru")
    p.add_argument("--source-lang", default="ja")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--interval", type=float, default=0.35)
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-assets", action="store_true")
    p.add_argument("--max-pages", type=int, default=None)
    p.set_defaults(func=cmd_all)

    p = sub.add_parser("years", help="показать доступные годы для модели")
    p.add_argument("--car", default="freed")
    p.add_argument("--year", default="2020")
    p.add_argument("--base", default="https://www.honda.co.jp")
    p.set_defaults(func=cmd_years, data=None, site_dir=None)

    p = sub.add_parser("status", help="показать состояние")
    _add_common(p)
    p.add_argument("--target", default="ru")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("freq", help="частотность фраз (блоков перевода)")
    _add_common(p)
    p.add_argument("--years", default=None, help="годы через запятую (по умолчанию все)")
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--min-count", type=int, default=1)
    p.add_argument("--min-chars", type=int, default=0)
    p.add_argument("--content", action="store_true",
                   help="без служебных блоков (опросы, навигация)")
    p.add_argument("--budget", action="store_true",
                   help="показать накопленные знаки для топ-N")
    p.add_argument("--csv", default=None, help="выгрузить полный список в CSV")
    p.add_argument("--json", default=None, help="выгрузить полный список в JSON")
    p.add_argument("--refresh", action="store_true", help="пересчитать частотность")
    p.set_defaults(func=cmd_freq)

    p = sub.add_parser("deepl", help="перевести самые частые фразы через DeepL")
    _add_common(p)
    p.add_argument("--years", default=None, help="годы через запятую (по умолчанию все)")
    p.add_argument("--budget", default="auto",
                   help="сколько знаков потратить: число или auto (остаток квоты)")
    p.add_argument("--top", type=int, default=None, help="не больше N фраз")
    p.add_argument("--min-count", type=int, default=1)
    p.add_argument("--min-chars", type=int, default=0)
    p.add_argument("--all", action="store_true",
                   help="включать служебные блоки (опросы, навигацию)")
    p.add_argument("--menus", action="store_true",
                   help="перевести заголовки бокового меню (contentsDB.json)")
    p.add_argument("--salvage", action="store_true",
                   help="спасти блоки с изменённой разметкой через плейсхолдеры тегов")
    p.add_argument("--salvage-min-chars", type=int, default=20)
    p.add_argument("--salvage-max-tags", type=int, default=4)
    p.add_argument("--dry-run", action="store_true", help="только показать план")
    p.add_argument("--retry-failed", action="store_true",
                   help="повторить блоки, ранее не прошедшие проверку разметки")
    p.add_argument("--refresh", action="store_true", help="пересчитать частотность")
    p.set_defaults(func=cmd_deepl)

    p = sub.add_parser("verify", help="проверить ссылки, страницы и остатки японского")
    _add_common(p)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("serve", help="локальный HTTP-сервер")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--site", dest="site_dir", type=Path, default=PROJECT_DIR / "site")
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)
