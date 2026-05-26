# Makefile
SHELL = /bin/bash

# Load .env file if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# help
.PHONY: help
help:
	@echo "Commands:"
	@echo "run     : starts backend (uvicorn) and frontend (streamlit) together."
	@echo "backend : starts only the uvicorn backend on port 8000."
	@echo "frontend: starts only the streamlit frontend on port 8501."
	@echo "venv    : creates a virtual environment."
	@echo "style   : executes style formatting."
	@echo "test    : runs test suite with pytest."
	@echo "clean   : cleans all unnecessary files."

# Testing
.PHONY: test
test:
	pytest tests/ -v

# Run both backend and frontend
.PHONY: run backend frontend
run:
	@echo "Starting backend and frontend..."
	$(MAKE) backend &
	$(MAKE) frontend

backend:
	uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

frontend:
	streamlit run streamlit/ScopingReview_app.py --server.port 8501 --server.address 0.0.0.0

# Styling
.PHONY: style
style:
	black .
	flake8
	python3 -m isort .

# Environment
.ONESHELL:
venv:
	python3 -m venv venv
	source venv/bin/activate && \
	python3 -m pip install pip setuptools wheel && \
	python3 -m pip install -e .

# Cleaning
.PHONY: clean
clean: style
	find . -type f -name "*.DS_Store" -ls -delete
	find . | grep -E "(__pycache__|\.pyc|\.pyo)" | xargs rm -rf
	find . | grep -E ".pytest_cache" | xargs rm -rf
	find . | grep -E ".ipynb_checkpoints" | xargs rm -rf
	rm -f .coverage

