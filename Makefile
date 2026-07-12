.PHONY: test lint run

test:
	pytest

lint:
	ruff check .

run:
	streamlit run app.py
