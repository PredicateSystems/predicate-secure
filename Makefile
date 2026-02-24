.PHONY: hooks lint test dev-install format format-python format-docs lint-docs build clean

dev-install:
	python -m pip install -e ".[dev]"

hooks:
	pre-commit install

lint:
	pre-commit run --all-files

test:
	python -m pytest -q

format: format-python format-docs

format-python:
	pre-commit run black --all-files
	pre-commit run isort --all-files
	pre-commit run pyupgrade --all-files

format-docs:
	pre-commit run trailing-whitespace --all-files
	pre-commit run end-of-file-fixer --all-files
	pre-commit run mixed-line-ending --all-files

lint-docs:
	pre-commit run markdownlint-cli2

build:
	python -m pip install build
	python -m build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
