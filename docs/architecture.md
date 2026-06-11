# Architecture

## Manager / Workflow Pattern

Each scoping review step follows a two-module pattern:

- **Manager** -- orchestrates file I/O, data manipulation, and step-level logic
- **Workflow** -- core business logic and LLM interactions via `aiweb_common.WorkflowHandler`

```
FastAPI Router (app/v01/scoping/*.py)
       |
Manager (ScopingReview/*/Manager.py)
       |
Workflow (ScopingReview/*/Workflow.py)
```

## Per-Request LLM Credentials

Every LLM-calling endpoint requires client-supplied credentials -- there are no
server-side defaults or fallbacks:

- **JSON body**: `openai_compatible_endpoint`, `openai_compatible_model`
- **Header**: `Authorization: Bearer <api_key>`

LLM clients are instantiated per-request, never as global singletons.

## Base Classes

All workflows extend `aiweb_common.WorkflowHandler` from the `llm_utils` package.
All managers extend [`BaseManager`](core/base-manager.md), which provides shared
utilities for PubMed interaction, Excel/DOCX output, and full-text retrieval.

## Endpoints

| Route | Purpose | Response |
|-------|---------|----------|
| `POST /v01/scoping/step1/` | Initial PubMed search | base64 XLSX |
| `POST /v01/scoping/step2/keywords/` | Extract keywords | JSON keyword lists |
| `POST /v01/scoping/step2/iteration/` | Refine search with keywords | base64 XLSX |
| `POST /v01/scoping/step3/` | Categorize articles | base64 XLSX |
| `POST /v01/scoping/step4/` | Summarize by category | base64 DOCX |
| `POST /v01/scoping/step5/` | Generate draft review | base64 DOCX |
| `POST /v01/standalone/summary/` | One-step research summary | base64 DOCX |
| `POST /v01/standalone/bibliography/` | Convert citations to BibTeX | base64 BIB |
| `GET /health` | Health check | JSON status |
