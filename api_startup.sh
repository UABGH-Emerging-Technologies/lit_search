#!/usr/bin/env bash
set -e

# Start the FastAPI app using Uvicorn
exec uvicorn app.server:app --host 0.0.0.0 --port 8000