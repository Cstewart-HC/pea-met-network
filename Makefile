.PHONY: install test lint check

install:
	python -m pip install -r requirements.txt -r requirements-dev.txt

test:
	pytest

lint:
	ruff check .

check: lint test
