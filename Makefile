.PHONY: install_dev lint test

install_dev:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install homeassistant pytest pytest-homeassistant-custom-component
	.venv/bin/pre-commit install

lint:
	.venv/bin/ruff check custom_components tests
	.venv/bin/ruff format --check custom_components tests

test:
	.venv/bin/pytest tests/ -v
