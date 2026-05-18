# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lit Search is a FastAPI application that automates literature searches and scoping reviews. It orchestrates a five-step workflow — initial PubMed search, keyword extraction, iterative refinement, article categorization, summarization, and draft generation — plus standalone bibliography and summary endpoints. Files are exchanged as base64-encoded Excel/Word documents.

## Commands

```bash
# Setup
make venv && source venv/bin/activate

# Run API server
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

# Run with Docker
docker-compose up --build --force-recreate   # exposes port 8000

# Lint & format
make style                                    # runs black, flake8, isort

# Tests
pytest                                        # all tests
pytest tests/fastapi_tests/v01/scoping/       # scoping workflow tests
pytest tests/fastapi_tests/v01/standalone/    # standalone feature tests
pytest tests/fastapi_tests/ -k test_name      # single test by name

# Clean
make clean
```

## Architecture

**Entry point:** `app/server.py` — FastAPI app that mounts versioned routers and a `/health` endpoint.

### Endpoints

| Route | Purpose | Response |
|-------|---------|----------|
| `POST /v01/scoping/step1/` | Initial PubMed search from research question | base64 XLSX |
| `POST /v01/scoping/step2/keywords/` | Extract keywords from results | JSON keyword lists |
| `POST /v01/scoping/step2/iteration/` | Refine search with keywords | base64 XLSX |
| `POST /v01/scoping/step3/` | Categorize articles | base64 XLSX |
| `POST /v01/scoping/step4/` | Summarize by category | base64 DOCX |
| `POST /v01/scoping/step5/` | Generate draft review | base64 DOCX |
| `POST /v01/standalone/summary/` | One-step research summary | base64 DOCX |
| `POST /v01/standalone/bibliography/` | Convert citations to BibTeX | base64 BIB |
| `GET /health` | Health check | JSON status |

### Manager / Workflow Pattern

Each step has two modules under `ScopingReview/`:
- `Manager.py` — orchestrates file I/O and step-level logic
- `Workflow.py` — core business logic and LLM interactions via `aiweb_common.WorkflowHandler`

```
FastAPI Router (app/v01/scoping/*.py)
       ↓
Manager (ScopingReview/*/Manager.py)
       ↓
Workflow (ScopingReview/*/Workflow.py)
```

### Per-Request LLM Credentials (Critical Policy)

Every LLM-calling endpoint requires client-supplied credentials — **no server-side defaults or fallbacks**:
- **JSON body**: `openai_compatible_endpoint`, `openai_compatible_model`
- **Header**: `Authorization: Bearer <api_key>`

LLM clients are instantiated per-request, never as global singletons.

### Key Base Class

All workflows extend `aiweb_common.WorkflowHandler` from the `llm_utils` package. Always search `llm_utils`/`aiweb_common` for existing functionality before writing new code.

### Configuration

- `ScopingReview_config/config.py` — paths, output filenames, MIME types, thresholds
- `ScopingReview_config/app_config.py` — API keys sourced from environment
- `ScopingReview_config/prompt_config.py` — LLM prompts for each workflow step
- `ScopingReview_config/boilerplate.py` — boilerplate text templates

### External APIs

- **PubMed Entrez API** (via Biopython) — article retrieval
- **Library Key API** — full-text access links

## Testing

Tests live in `tests/fastapi_tests/v01/` organized by workflow (`scoping/`, `standalone/`). All LLM calls are mocked — no real API calls in tests. Mocks cover `ChatOpenAI`, `PromptyHandler`, `RAGResponseHandler`, and `tiktoken`. Test fixtures in `conftest.py` provide a FastAPI `TestClient`, encoded file fixtures, and request helpers.

## Code Conventions

- **Python ≥ 3.10** with full type annotations everywhere
- **Formatting:** Black (line length 100), isort (profile=black), flake8. Config in `pyproject.toml`
- **Naming:** `snake_case` for modules/functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants/enums, `_leading_underscore` for private, `*_async` suffix for async functions
- **Docstrings:** Google style on public interfaces
- **Reuse** `aiweb_common` classes/methods; propose additions to `llm_utils` rather than editing it directly

## Restricted Files

Never read, write, or commit: `.env`, `.env.*`, `.venv/`, `supersecrets.txt`, `credentials.json`, `*.pem`, `*.key`, `secrets/`, or any file in `data/` containing PHI/PII.

## Package Management

- `requirements.in` has direct dependencies; `requirements.txt` is the locked output (pip-compile)
- `uv` is the preferred package manager
- Editable install: `pip install -e .` (uses `setup.py`)
