# Honda Freed data branch

This branch contains the downloaded source data and Russian translations used to
build the offline manual:

- `data/raw/` — crawled HTML pages and menu JSON;
- `data/assets/` — mirrored images, CSS, JS, fonts and JSON assets;
- `data/translated/` — translated HTML, menu data and tooltip data;
- `data/translate.sqlite` — translation cache and DeepL overrides;
- `data/manifests/`, `data/reports/`, `data/frequencies/` — crawl/build metadata.

The source pages are from:

https://www.honda.co.jp/ownersmanual/webom/jpn/freed/<year>/

Build the site and ISOs with the code from the `main` branch.
