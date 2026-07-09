.PHONY: dev sync lint clean

dev:
	uv run uvicorn main:app --reload

sync:
	uv sync

lint:
	uv run ruff check .

clean:
	rm -rf .ruff_cache __pycache__