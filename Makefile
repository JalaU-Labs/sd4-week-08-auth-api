.PHONY: help install lint format format-check typecheck test test-cov check run clean

help:
	@echo "Available targets:"
	@echo "  install       Install dependencies with uv"
	@echo "  lint          Run ruff check"
	@echo "  format        Run ruff format"
	@echo "  format-check  Verify formatting"
	@echo "  typecheck     Run mypy on src/"
	@echo "  test          Run pytest"
	@echo "  test-cov      Run pytest with coverage"
	@echo "  check         Run lint + format-check + typecheck + test"
	@echo "  run           Run the API locally on port 8000"
	@echo "  clean         Remove caches and coverage artifacts"

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy src

test:
	uv run pytest -q

test-cov:
	uv run pytest --cov=sd4_week_08_auth_api --cov-report=term-missing --cov-report=xml

check: lint format-check typecheck test

run:
	uv run uvicorn sd4_week_08_auth_api.main:app --reload --host 0.0.0.0 --port 8000

clean:
	rm -rf .coverage htmlcov coverage.xml .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
