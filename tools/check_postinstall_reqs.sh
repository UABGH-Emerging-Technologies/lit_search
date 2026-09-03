#!/usr/bin/env bash
# Keep the requirements.txt copy embedded in environment/postInstall in sync.
#
# Code Ocean builds the capsule environment before /code exists, so postInstall
# cannot read code/requirements.txt -- it carries a verbatim copy inside a
# heredoc. If that copy drifts from code/requirements.txt, the capsule
# environment is built from stale pins and the run is no longer reproducible.
#
#   check  (default)  fail if the embedded copy differs from code/requirements.txt
#   sync              rewrite the embedded copy from code/requirements.txt
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
MODE="${1:-check}"

case "$MODE" in
    check|sync) ;;
    *) echo "usage: check_postinstall_reqs.sh {check|sync}" >&2; exit 2 ;;
esac

exec python3 - "$REPO_ROOT" "$MODE" <<'PY'
import difflib
import os
import shutil
import sys
import tempfile

root, mode = sys.argv[1], sys.argv[2]
post = os.path.join(root, "environment", "postInstall")
reqs = os.path.join(root, "code", "requirements.txt")

for path in (post, reqs):
    if not os.path.isfile(path):
        sys.stderr.write("error: missing %s\n" % path)
        raise SystemExit(2)

START = "cat > /opt/lit_search_requirements.txt <<'REQS'"
END = "REQS"

with open(post, encoding="utf-8", newline="") as fh:
    lines = fh.readlines()
with open(reqs, encoding="utf-8", newline="") as fh:
    wanted = fh.readlines()

start = next((i for i, ln in enumerate(lines) if ln.rstrip("\n") == START), None)
if start is None:
    sys.stderr.write(
        "error: start marker not found in environment/postInstall:\n  %s\n" % START
    )
    raise SystemExit(2)

end = next(
    (i for i in range(start + 1, len(lines)) if lines[i].rstrip("\n") == END), None
)
if end is None:
    sys.stderr.write(
        "error: end marker %r not found after the start marker in "
        "environment/postInstall\n" % END
    )
    raise SystemExit(2)

embedded = lines[start + 1 : end]
rel = "environment/postInstall"

if mode == "check":
    if embedded == wanted:
        print("%s: embedded requirements match code/requirements.txt" % rel)
        raise SystemExit(0)
    sys.stderr.write(
        "".join(
            difflib.unified_diff(
                embedded, wanted, fromfile="%s (embedded)" % rel,
                tofile="code/requirements.txt", n=2,
            )
        )
    )
    sys.stderr.write(
        "\n%s: embedded requirements are STALE. The Code Ocean environment would\n"
        "  be built from different pins than the repo declares. Run: make capsule-fix\n"
        % rel
    )
    raise SystemExit(1)

# mode == "sync"
if embedded == wanted:
    print("%s: already in sync" % rel)
    raise SystemExit(0)

out = lines[: start + 1] + wanted + lines[end:]
directory = os.path.dirname(post)
fd, tmp = tempfile.mkstemp(dir=directory, prefix=".postInstall.")
try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(out)
    shutil.copymode(post, tmp)
    os.replace(tmp, post)
except BaseException:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise
print(
    "%s: embedded requirements updated (%d -> %d lines)"
    % (rel, len(embedded), len(wanted))
)
PY
