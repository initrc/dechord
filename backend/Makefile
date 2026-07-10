.PHONY: dev sync lint test clean

dev:
	uv run fastapi dev

sync:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

clean:
	rm -rf .ruff_cache __pycache__