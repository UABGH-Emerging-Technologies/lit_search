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

## Running the API

### Local

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker compose up --build
```

This exposes the API on port 8000 with a health check at `/health`.

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
