# Lit Search

Automated literature searches and scoping reviews powered by LLMs and PubMed.

Lit Search is a FastAPI application that orchestrates a multi-step workflow for
conducting scoping reviews: initial PubMed search, keyword extraction, iterative
refinement, article categorization, summarization, and draft generation. It also
provides standalone endpoints for quick literature summaries and BibTeX bibliography
conversion.

## Quick Links

- [Getting Started](getting-started.md) -- installation and running the app
- [Architecture](architecture.md) -- how the codebase is organized
- [Scoping Workflow](scoping/overview.md) -- the 5-step scoping review pipeline
- [Standalone Tools](standalone/summary.md) -- one-shot summary and bibliography endpoints
- [Configuration](config/config.md) -- constants, prompts, and settings

## API Documentation

When the server is running, interactive API docs are available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Citation

If you found this helpful in your work, please cite:

> *Citation details forthcoming.*
