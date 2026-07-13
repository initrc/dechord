.PHONY: dev sync lint typecheck test clean

dev:
	uv run fastapi dev

sync:
	uv sync

lint:
	uv run ruff check .

typecheck:
	uv run mypy app tests

test:
	uv run pytest

clean:
	rm -rf .ruff_cache __pycache__