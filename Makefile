VENV := .venv
PY := $(VENV)/bin/python

CAR ?= freed
YEAR ?= 2020
PROVIDER ?= google-web
TARGET ?= ru
TOP ?= 40
BUDGET ?= auto

.PHONY: all venv crawl assets translate build serve status verify iso years all-years freq deepl deepl-menus clean

all: crawl translate build

all-years: venv
	@for y in $$($(PY) -m webom years --car $(CAR)); do \
		echo "=== $(CAR) $$y ==="; \
		$(PY) -m webom crawl --car $(CAR) --year $$y && \
		$(PY) -m webom translate --car $(CAR) --year $$y --provider $(PROVIDER) --target $(TARGET) && \
		$(PY) -m webom build --car $(CAR) --year $$y --target $(TARGET) || exit 1; \
	done

venv: $(VENV)/.installed

$(VENV)/.installed: requirements.txt
	python3 -m venv --system-site-packages $(VENV)
	$(PY) -m pip install -q -r requirements.txt
	touch $(VENV)/.installed

crawl: venv
	$(PY) -m webom crawl --car $(CAR) --year $(YEAR)

assets: venv
	$(PY) -m webom assets --car $(CAR) --year $(YEAR)

translate: venv
	$(PY) -m webom translate --car $(CAR) --year $(YEAR) --provider $(PROVIDER) --target $(TARGET)

build: venv
	$(PY) -m webom build --car $(CAR) --year $(YEAR) --target $(TARGET)

serve: venv
	$(PY) -m webom serve

verify: venv
	$(PY) -m webom verify

iso: venv
	$(PY) tools/make_iso.py

status: venv
	$(PY) -m webom status --car $(CAR) --year $(YEAR) --target $(TARGET)

freq: venv
	$(PY) -m webom freq --car $(CAR) --top $(TOP) --content --budget

deepl: venv
	$(PY) -m webom deepl --car $(CAR) --budget $(BUDGET)

deepl-menus: venv
	$(PY) -m webom deepl --car $(CAR) --menus --budget $(BUDGET)

years: venv
	$(PY) -m webom years --car $(CAR)

clean:
	rm -rf data site
