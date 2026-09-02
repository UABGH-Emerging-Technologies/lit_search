#!/usr/bin/env bash
# lit_search — Code Ocean entry point.
#
# In the capsule, mark this script as "File to Run": Code Ocean then generates
# the master /code/run wrapper itself and invokes this script (e.g. `bash
# run.sh`) with the working directory set to /code. The script also works when
# invoked directly (./run.sh) for local testing.
#
# SECURITY: secrets arrive only as environment variables (Code Ocean User
# Secrets) and are never echoed. No xtrace. No .env reads.
set -euo pipefail

# Resolve the repo root from this script's own location — robust to being
# invoked as `bash run.sh`, `./run.sh`, or via an absolute path.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# If the repo tree isn't beside this script (e.g. the repo was imported into a
# subfolder of /code while run.sh sits at the top), locate it by the driver.
if [[ ! -f "$REPO_ROOT/scripts/capsule_driver.py" ]]; then
  DRIVER="$(find "$REPO_ROOT" -maxdepth 4 -path '*/scripts/capsule_driver.py' -print -quit)"
  if [[ -z "$DRIVER" ]]; then
    echo "error: scripts/capsule_driver.py not found under $REPO_ROOT." >&2
    echo "The full repository tree (app/, scripts/, ScopingReview/, ...) must be" >&2
    echo "inside the capsule's code folder alongside run.sh." >&2
    exit 1
  fi
  REPO_ROOT="$(dirname "$(dirname "$DRIVER")")"
fi
if [[ ! -f "$REPO_ROOT/app/server.py" ]]; then
  echo "error: found the driver but not app/server.py under $REPO_ROOT —" >&2
  echo "the application tree is incomplete in the code folder." >&2
  exit 1
fi

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT"

# The environment is built from a copy of requirements.txt embedded in
# environment/postInstall (/code is invisible at build time). Warn on drift.
if [[ -f /opt/lit_search_requirements.txt ]] \
  && ! cmp -s /opt/lit_search_requirements.txt "$REPO_ROOT/requirements.txt"; then
  echo "warning: this environment was built from a different requirements.txt than the" >&2
  echo "         repo's — regenerate environment/postInstall and rebuild the environment." >&2
fi
# /code is ephemeral on Code Ocean (writes are discarded after the run);
# skip .pyc emission rather than litter it.
export PYTHONDONTWRITEBYTECODE=1

# Outputs: an explicitly-set $RESULTS_DIR wins, else the Code Ocean /results
# mount (the only folder persisted after a Reproducible Run), else ./results.
if [[ -z "${RESULTS_DIR:-}" ]]; then
  if [[ -d "/results" ]]; then
    RESULTS_DIR="/results"
  else
    RESULTS_DIR="$REPO_ROOT/results"
  fi
fi
mkdir -p "$RESULTS_DIR"
export RESULTS_DIR

# Some base images expose only `python`; prefer python3 when present.
PYTHON_BIN="$(command -v python3 || command -v python)"

exec "$PYTHON_BIN" "$REPO_ROOT/scripts/capsule_driver.py" "$@"
