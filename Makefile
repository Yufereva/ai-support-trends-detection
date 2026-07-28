.PHONY: setup test lint run api

setup:
	python data/synthetic/import_to_app.py apply

test:
	pytest

lint:
	ruff check .

run:
	streamlit run app.py

api:
	uvicorn api.main:app --reload --port 8000
