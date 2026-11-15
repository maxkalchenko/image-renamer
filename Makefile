PYTHON ?= python

.PHONY: install hooks lint format format-check test check

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

hooks:
	$(PYTHON) -m pre_commit install

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

format-check:
	$(PYTHON) -m ruff format --check .

test:
	$(PYTHON) -m pytest

check: lint format-check test
