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
	@echo "run       : starts backend (uvicorn) and frontend (streamlit) together."
	@echo "backend   : starts only the uvicorn backend on port 8000."
	@echo "frontend  : starts only the streamlit frontend on port 8501."
	@echo "venv      : creates a virtual environment."
	@echo "style     : executes style formatting."
	@echo "test      : runs test suite with pytest."
	@echo "docs      : builds documentation site (strict mode)."
	@echo "docs-serve: starts live-reloading documentation server."
	@echo "clean     : cleans all unnecessary files."
	@echo "capsule   : verifies the Code Ocean capsule environment is consistent."
	@echo "scan-secrets: scans every tracked file for secret-shaped content."

# Testing
.PHONY: test
test:
	cd code && pytest tests/ -v

# Run both backend and frontend
.PHONY: run backend frontend
run:
	@echo "Starting backend and frontend..."
	$(MAKE) backend &
	$(MAKE) frontend

backend:
	cd code && uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd code && streamlit run streamlit/ScopingReview_app.py --server.port 8501 --server.address 0.0.0.0

# Styling
.PHONY: style
style:
	cd code && black . && flake8 && python3 -m isort .

# Environment
.ONESHELL:
venv:
	python3 -m venv venv
	source venv/bin/activate && \
	python3 -m pip install pip setuptools wheel && \
	python3 -m pip install -e ./code

# Documentation
.PHONY: docs docs-serve
docs:
	mkdocs build

docs-serve:
	mkdocs serve

# Cleaning
.PHONY: clean
clean: style
	find . -type f -name "*.DS_Store" -ls -delete
	find . | grep -E "(__pycache__|\.pyc|\.pyo)" | xargs rm -rf
	find . | grep -E ".pytest_cache" | xargs rm -rf
	find . | grep -E ".ipynb_checkpoints" | xargs rm -rf
	rm -f .coverage


# Security
.PHONY: scan-secrets
scan-secrets:
	python3 tools/scan_secrets.py
	python3 code/capsule/scrub.py code/demo_fixtures

# Code Ocean capsule
#
# environment/Dockerfile carries its own cache key on line 1 as
# `# hash:sha256:<sha256 of lines 2..EOF>`. Code Ocean rebuilds the environment
# only when that value changes, so a hand-edited Dockerfile with a stale header
# is silently ignored and the old image is reused. environment/postInstall
# likewise embeds a verbatim copy of code/requirements.txt, because /code does not
# exist at environment build time. Both must be kept honest.
.PHONY: capsule capsule-check capsule-fix
capsule: capsule-check

capsule-check:
	@rc=0; \
	tools/co_env_hash.sh check || rc=1; \
	tools/check_postinstall_reqs.sh check || rc=1; \
	exit $$rc

capsule-fix:
	tools/check_postinstall_reqs.sh sync
	tools/co_env_hash.sh fix
