# Honda Freed — локальная копия руководства + русский перевод

Скрипты обходят `https://www.honda.co.jp/ownersmanual/webom/jpn/<model>/<year>/`,
скачивают HTML и все ресурсы, переводят текст и собирают офлайн-сайт с двумя версиями:

- `/ownersmanual/webom/jpn/freed/2020/…` — японский оригинал;
- `/ru/ownersmanual/webom/jpn/freed/2020/…` — русский перевод.

Сейчас собраны все годы модели FREED: **2017, 2020, 2023, 2025, 2026**.

Подробный план и ограничения — в [PLAN.md](PLAN.md).

## Установка

```bash
cd /home/anatoly/prj/freed
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

или просто `make venv`.

## Быстрый старт

```bash
make crawl        # ~360 страниц + картинки/CSS/JS
make translate    # перевод (по умолчанию google-web, без ключа)
make build
make serve        # http://127.0.0.1:8000/
```

То же самое одной командой:

```bash
.venv/bin/python -m webom all
```

Все годы модели — одной командой (`make all-years`):

```bash
make all-years CAR=freed PROVIDER=google-web TARGET=ru
```

## Запуск на Windows 10/11

Python **не нужен**. Используется встроенный в Windows 10/11 PowerShell 5.1 и
его .NET `HttpListener`; права администратора не требуются. Нужна только уже
собранная папка `site/` (её можно скопировать с Linux/WSL целиком).

Самый простой способ — двойной клик по `start-freed.cmd`: откроется окно сервера
и браузер с `http://127.0.0.1:8000/`. Закрытие окна или `Ctrl+C` останавливает сервер.

То же самое из PowerShell:

```powershell
cd C:\path\to\freed
.\start-freed.ps1

# другой порт
.\start-freed.ps1 -Port 8080

# без автоматического открытия браузера
.\start-freed.ps1 -NoBrowser

# сервер в отдельном окне; остановка — stop-freed.cmd
.\start-freed.ps1 -NewWindow
```

Если PowerShell блокирует выполнение скриптов, используйте `.cmd`-обёртки
(`start-freed.cmd`, `stop-freed.cmd`) — они запускают PowerShell с
`-ExecutionPolicy Bypass`. Если порт занят, скрипт автоматически попробует
следующие 20 портов и покажет фактический URL.

`serve-freed.ps1` — нативный сервер для Windows. Он умеет то же, что и Linux-версия
`serve.py`: если скрипт Honda запрашивает отсутствующий файл под `/ru/...`,
сервер пробует тот же путь без `/ru` или подставляет год. Поэтому не заменяйте
его обычным `python -m http.server`, если хотите видеть все картинки и меню.

## ISO-образы

`make iso` собирает два образа:

```text
build/Honda Freed 2 Owners Manual.iso   2017, 2020, 2023   ~243 МиБ
build/Honda Freed 3 Owners Manual.iso   2025, 2026         ~139 МиБ
```

Внутри каждого — только его годы, данные сайта и средства запуска:

```text
site/                 локальная копия выбранных годов
autorun.inf           автозапуск Windows
start.cmd             запуск для Windows (без Python)
serve-freed.ps1       нативный сервер Windows
start-linux.sh        запуск для Linux
README.txt            инструкция + исходные URL
```

В `README.txt` указано, что это локальная копия страниц:

```text
https://www.honda.co.jp/ownersmanual/webom/jpn/<model>/<year>/
```

и перечислены конкретные URL для годов, входящих в образ.

Windows 10/11 часто игнорирует `autorun.inf` с CD/USB из соображений
безопасности — тогда просто запустите `start.cmd`. На Linux:

```bash
./start-linux.sh
```

### Окно условий использования

В локальной копии окно «Условия использования услуги просмотра инструкций»
отключено навсегда: сборка патчит `agreement()` / `showAgreement()` в JS и
добавляет к `common.js`/`library.js` версионный параметр, чтобы браузер не взял
старый закэшированный файл. Отдельно нажимать «Согласен» больше не нужно.

### Если остались 404

- Запускайте обновлённый `start-freed.cmd` / `start-freed.ps1`: он вызывает
  нативный `serve-freed.ps1`, а не Python и не старый `python -m http.server`.
- Нажмите `Ctrl+F5`, чтобы сбросить закэшированный `common.js`.
- Сообщения про `slick.eot`, `slick.woff` и т. п. — это закомментированный
  `@font-face` в CSS самого Honda; браузер такие URL не запрашивает.

## GitHub

Репозиторий разделён на две ветки:

- `main` — код обхода, перевода, сборки, упаковки, документация и GitHub Actions;
- `Freed` — выкачанные данные и переводы: `data/raw`, `data/assets`,
  `data/translated`, `data/translate.sqlite`, манифесты и отчёты.

В `main` нет `site/`, `data/` и ISO: они генерируются. Workflow
`.github/workflows/iso.yml` забирает ветку `Freed`, собирает сайт и оба ISO,
проверяет его через `webom verify` и выкладывает архивы как artifacts. При пуше
тега `v*` ISO дополнительно прикрепляются к GitHub Release.

Секреты в репозиторий не коммитятся. Ключ DeepL задаётся только через
переменную окружения:

```bash
export DEEPL_API_KEY='xxxxxxxx:fx'
```

`.env`, `*.key`, `*.pem` и `secrets/` исключены в `.gitignore`; пример —
`.env.example`.

Лицензия — MIT, см. [LICENSE](LICENSE).

## Команды

```bash
# обход (--max-pages N для теста, --force для перекачки)
.venv/bin/python -m webom crawl --car freed --year 2020

# только ресурсы
.venv/bin/python -m webom assets --car freed --year 2020

# перевод; --limit N — первые N страниц
.venv/bin/python -m webom translate --car freed --year 2020 --provider google-web

# сборка site/
.venv/bin/python -m webom build --car freed --year 2020

# состояние и отчёт
.venv/bin/python -m webom status --car freed --year 2020

# доступные годы модели
.venv/bin/python -m webom years --car freed

# проверить ссылки, страницы и остатки японского
make verify

# собрать ISO
make iso

# локальный сервер (с фолбэком на общие ресурсы)
.venv/bin/python -m webom serve --port 8000
# или без зависимостей проекта:
python3 serve.py --port 8000 --site site

# частотность фраз (блоков перевода) по всем годам
.venv/bin/python -m webom freq --top 40 --content --budget

# выборочный DeepL: только самые частые фразы, в пределах остатка квоты
DEEPL_API_KEY=xxxxxxxx:fx .venv/bin/python -m webom deepl --dry-run --budget auto
DEEPL_API_KEY=xxxxxxxx:fx .venv/bin/python -m webom deepl --budget auto
```

## Перевод: провайдеры

| `--provider` | Переменные окружения | Примечание |
|---|---|---|
| `google-web` | — | по умолчанию; без ключа, ~2 запроса/сек |
| `deepl` | `DEEPL_API_KEY` | лучшее качество; free-ключ заканчивается на `:fx`; авторизация через `DeepL-Auth-Key` |
| `yandex` | `YANDEX_API_KEY`, `YANDEX_FOLDER_ID` | Yandex Cloud Translate |
| `ollama` | `OLLAMA_MODEL`, `OLLAMA_URL` | локально, медленно, 7.6 ГБ RAM мало для качества |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL` | любой OpenAI-совместимый API |

DeepL удобнее включать не для всего корпуса сразу, а выборочно — см. раздел
«Частотность и выборочный DeepL». Кэш переводов хранится в `data/translate.sqlite`
и общий для всех прогонов и годов. Сменить провайдера можно в любой момент —
старые переводы останутся, новые добавятся.

## Частотность и выборочный DeepL

Единица частотности — **блок перевода**: абзац, пункт списка, ячейка таблицы,
заголовок или plain-единица (`title`, `alt`, `meta`, `placeholder`). Один и тот же
блок, встретившийся на нескольких страницах и в разных годах, считается один раз
в кэше, но все его вхождения учитываются в частотности.

```bash
# топ всех блоков; --content убирает опросы/навигацию; --budget показывает
# накопленные знаки для топ-100/250/500/1000/2000/3000/5000
.venv/bin/python -m webom freq --top 40 --content --budget

# выгрузить полный список
.venv/bin/python -m webom freq --content --csv data/reports/freq.csv --json data/reports/freq.json
```

Результат кэшируется в `data/frequencies/freed.json` (пересчёт — `--refresh`,
~40 секунд на 1 245 страниц). В Top-10 по вхождениям входят служебные фразы
(«さらに詳しく», «取扱説明書トップ», вопросы анкеты), поэтому для содержательного
перевода используйте `--content` или `--min-chars`.

DeepL переводит выбранные блоки (по умолчанию — по убыванию частоты, пока хватает
бюджета) и складывает их в таблицу `overrides` базы `data/translate.sqlite`.
При сборке overrides имеют приоритет над обычным кэшем `google-web`, поэтому
переводить весь корпус заново не нужно.

```bash
export DEEPL_API_KEY=xxxxxxxx:fx

# план: сколько фраз и знаков будет отправлено (ключ нужен только для --budget auto)
.venv/bin/python -m webom deepl --dry-run --budget auto

# перевести самые частые содержательные блоки в пределах остатка квоты
.venv/bin/python -m webom deepl --budget auto

# только заголовки бокового меню 2025–2026
.venv/bin/python -m webom deepl --menus --budget auto

# применить overrides ко всем годам
for y in 2017 2020 2023 2025 2026; do
  .venv/bin/python -m webom translate --year "$y" && \
    .venv/bin/python -m webom build --year "$y"
done
```

Полезные ограничители: `--top N`, `--min-count N`, `--min-chars N`, `--all`
(включать служебные блоки), `--years 2020,2023`, `--retry-failed` (повторить
блоки, ранее не прошедшие проверку разметки). `--budget auto` запрашивает
`/v2/usage`, вычитает уже израсходованные знаки и оставляет запас 1 000 знаков.
Если DeepL изменил inline-разметку блока (например, выбросил `<sup>`), такой блок
не попадает в overrides и остаётся на переводе Google — это нормальный fallback.
Такие блоки запоминаются в таблице `deepl_failures`, чтобы повторный запуск не тратил
на них квоту. Для длинных блоков с небольшим числом тегов есть режим salvage:
теги заменяются плейсхолдерами, DeepL переводит текст, после чего теги
восстанавливаются и проверяется структура вложенности.

```bash
.venv/bin/python -m webom deepl --salvage --budget auto
```

Текущий прогон (2026-10-23): 20 699 уникальных блоков, 569 235 «биллинговых»
знаков текста. После дополнительного прохода DeepL покрыты все 20 699 блоков
страниц, 727 заголовков меню и подсказки на схемах; всего 21 580 overrides,
`deepl_failures` — 0. Израсходовано 638 208 из 1 000 000 знаков, осталось
361 792.

## Как устроен перевод

1. Из HTML вырезаются «листовые» текстовые блоки: абзацы, пункты списков, ячейки таблиц,
   заголовки — вместе с inline-разметкой (`<a>`, `<span>`, `<sup>`, `<br>`), чтобы сохранить
   ссылки, якоря и `id`.
2. Уникальные блоки батчами отправляются провайдеру; результат пишется в SQLite.
3. Если провайдер сломал разметку, блок переводится повторно по отдельным текстовым узлам.
4. Глоссарий `glossary/ru.json` применяется поверх перевода (замена терминов).
5. Атрибуты разметки (`style`, `class`, `href`, `id`, …) принудительно возвращаются
   к исходным значениям: переводчик не должен менять CSS и ссылки.

### Руководства нового формата (2025–2026)

В руководствах 2025 и 2026 боковое меню строится JavaScript из
`language/ja_JP/main/json/contentsDB.json`, а не из статического HTML. Скрипт
`crawl` находит такие JSON-базы, добавляет страницы `details/…` в обход и сохраняет
базы в `data/raw/…/language/…/json/`. При переводе заголовки меню (`L1`–`L5`)
переводятся тем же кэшем, а `build` кладёт японскую и русскую копии JSON в
`site/ownersmanual/…` и `site/ru/ownersmanual/…`. Записи меню без существующей
страницы отбрасываются. Поле `text` (поисковый индекс) в русской копии
заполняется текстом соответствующей переведённой страницы `details/…` или
`detailsnavi/…`, поэтому японского поискового текста в `site/ru` не остаётся.

### Подсказки на схемах

Всплывающие подписи на интерактивных схемах лежат не в HTML:

- 2025–2026: `language/ja_JP/main/json/visualindex_content.json`;
- 2017–2023: `pc/js/data/appearance.point.js` и `interior.point.js`
  (поля `caption`).

`webom translate` теперь переводит и эти данные: JSON-строки и `caption`
проходят через тот же кэш/overrides, а сборка кладёт русские копии в
`site/ru/...` и переключает старые страницы на переведённые JS-файлы.

## Структура

```
data/raw/freed/2020/…         сырой HTML
data/assets/www.honda.co.jp/… картинки, CSS, JS, шрифты
data/translated/ru/…          переведённый HTML и JSON-меню
data/manifests/               список страниц, JSON-баз и метаданные
data/reports/                 отчёты о покрытии перевода
data/frequencies/freed.json   частотность блоков по всем годам
data/translate.sqlite         кэш переводов + таблица overrides (DeepL)
site/                         готовый офлайн-сайт
start-freed.cmd / .ps1        запуск локальной копии в Windows
stop-freed.cmd / .ps1         остановка сервера, запущенного с -NewWindow
serve-freed.ps1               нативный сервер для Windows (без Python)
serve.py                      локальный сервер для Linux (stdlib) с фолбэком
packaging/                    шаблоны autorun/start.cmd/start-linux.sh для ISO
tools/make_iso.py             сборка ISO
webom/verify.py               проверка ссылок/страниц/остатков японского
```

## Масштабирование на все годы

```bash
for y in $(.venv/bin/python -m webom years --car freed); do
  .venv/bin/python -m webom crawl     --car freed --year "$y"
  .venv/bin/python -m webom translate --car freed --year "$y"
  .venv/bin/python -m webom build     --car freed --year "$y"
done
```

Для другой модели: `--car stepwgn` и т. п. (годовые индексы имеют тот же формат).

## Состояние сборки

| Год | Страниц (JA/RU) | Уникальных блоков | Пропущено переводов |
|---|---|---|---|
| 2017 | 321 / 321 | 10 107 | 0 |
| 2020 | 321 / 321 | 10 015 | 0 |
| 2023 | 150 / 150 | 4 731 | 0 |
| 2025 | 223 / 223 | 4 278 (+458 заголовков меню) | 0 |
| 2026 | 230 / 230 | 4 465 (+481 заголовок меню) | 0 |

Проверка после DeepL (`make verify`): 1 245 страниц, 26 164 локальные
ссылки/ресурса — битых нет; все `id` сохранены; реального японского текста
в русских страницах не осталось (кроме служебной подписи «Открыть оригинал
(日本語)»). DeepL покрывает все 20 699 уникальных блоков страниц, 727 заголовков
меню и подсказки на схемах.

В 2026 году 74 источника недоступны: 69 записей `contentsDB.json` — это пустые
разделы-заголовки без собственной страницы, ещё 5 — служебные страницы старого
шаблона (`search.html` и т. п.). Они пропускаются и не попадают в меню.

## Ограничения

- Текст, впечатанный в PNG-иллюстрации, не переводится. Это отдельный этап (OCR:
  `tesseract-ocr-jpn`), в v1 не реализован.
- Машинный перевод требует вычитки, особенно предупреждения и разделы безопасности.
- Сайт рассчитан на запуск через `webom serve` (корневые ссылки). Русская версия
  использует общие картинки из японского дерева, поэтому не дублирует десятки мегабайт.
- Поиск по руководству (внешний сервис Honda) отключён; при необходимости можно
  добавить локальный индекс позже.
