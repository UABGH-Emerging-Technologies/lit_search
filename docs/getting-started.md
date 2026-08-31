# Getting Started

## Installation

```bash
# Clone the repository
git clone https://github.com/UABGH-Emerging-Technologies/lit_search.git
cd lit_search

# Create a virtual environment and install
make venv
source venv/bin/activate
```

To install documentation dependencies:

```bash
pip install -e ".[docs]"
```

## Configuration

Copy the environment template and fill in your API keys:

```bash
cp .env.example .env
```

The template documents each value. Keep the variable names lowercase — they
must match the Docker secret names exactly. For file-based secrets instead of
a `.env`, see the `secrets:` block in `docker-compose.yml`.

## Running the API

### Local

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

For a host run the `.env` values must be exported into the environment —
`make run` (or `make backend` / `make frontend`) does this for you.

### Docker

```bash
docker compose up --build
```

Compose auto-loads `.env` and delivers each value as a Docker secret at
`/run/secrets/<name>`. This exposes the API on port 8000 with a health check
at `/health`, and the Streamlit frontend on port 8501.

## Running Tests

```bash
pytest                                        # all tests
pytest tests/fastapi_tests/v01/scoping/       # scoping workflow tests
pytest tests/fastapi_tests/v01/standalone/    # standalone feature tests
```

## Building Documentation

```bash
make docs          # build static site
make docs-serve    # live-reloading preview
```
