#!/usr/bin/env bash
# Manage the cache-key header on a Code Ocean environment/Dockerfile.
#
# Code Ocean records the environment's cache key on line 1 of environment/Dockerfile
# as `# hash:sha256:<hex>`, where <hex> is the SHA-256 of the file from line 2 to
# end-of-file, verbatim. Code Ocean compares that header against the previous build
# to decide whether to rebuild the environment or reuse the cached image.
#
# Consequence: editing the Dockerfile body by hand without updating the header makes
# Code Ocean conclude nothing changed and silently reuse the STALE image. The edit
# appears saved but never deploys.
#
# Second consequence: the hash covers the Dockerfile ONLY. environment/postInstall
# does all the apt/pip work and carries the pinned dependency lock, but changing it
# does not by itself change the Dockerfile -- so a pins bump can leave the cached
# image in place. To close that hole we keep a digest of postInstall inside the
# Dockerfile body on a `# postInstall-sha256:` line, so any postInstall change
# necessarily changes the body, the header, and therefore the cache key.
#
#   check   verify the header and the postInstall digest; exit 1 if either is stale
#   fix     refresh the postInstall digest, then the header (idempotent)
#   print   print the correct header hash for the current body
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
MODE="${1:-}"
FILE="${2:-$REPO_ROOT/environment/Dockerfile}"

case "$MODE" in
    check|fix|print) ;;
    *)
        cat >&2 <<'USAGE'
usage: co_env_hash.sh {check|fix|print} [FILE]

  check   verify line 1 matches the body hash and the postInstall digest is current
  fix     refresh the postInstall digest and rewrite line 1 (idempotent)
  print   print the correct hash for the body, then exit

FILE defaults to <repo root>/environment/Dockerfile.
USAGE
        exit 2
        ;;
esac

exec python3 - "$FILE" "$MODE" "$REPO_ROOT" <<'PY'
import hashlib
import os
import re
import shutil
import sys
import tempfile

path, mode, root = sys.argv[1], sys.argv[2], sys.argv[3]

if not os.path.isfile(path):
    sys.stderr.write(
        "error: %s does not exist.\n"
        "  A Code Ocean capsule needs environment/Dockerfile. Create it in the\n"
        "  capsule's Environment panel, or commit one here and sync.\n" % path
    )
    raise SystemExit(2)

HEADER_RE = re.compile(rb"^# hash:sha256:([0-9a-f]{64})\r?\n$")
MARKER_RE = re.compile(rb"^# postInstall-sha256: ([0-9a-f]{64})\b.*\r?\n$")
MARKER_NOTE = b"  (managed by tools/co_env_hash.sh)\n"

post = os.path.join(root, "environment", "postInstall")
post_digest = None
if os.path.isfile(post):
    with open(post, "rb") as fh:
        post_digest = hashlib.sha256(fh.read()).hexdigest().encode()

with open(path, "rb") as fh:
    lines = fh.readlines()

header = HEADER_RE.match(lines[0]) if lines else None
body = lines[1:] if header else lines[:]


def body_hash(body_lines):
    h = hashlib.sha256()
    for ln in body_lines:
        h.update(ln)
    return h.hexdigest().encode()


def marker_index(body_lines):
    for i, ln in enumerate(body_lines):
        if MARKER_RE.match(ln):
            return i
    return None


def marker_line(digest):
    return b"# postInstall-sha256: " + digest + MARKER_NOTE


rel = os.path.relpath(path, root)

if mode == "print":
    sys.stdout.write(body_hash(body).decode() + "\n")
    raise SystemExit(0)

if mode == "check":
    failures = []
    if header is None:
        failures.append(
            "no '# hash:sha256:<64 hex>' header on line 1 -- Code Ocean uses that\n"
            "  line as the environment cache key."
        )
    else:
        actual, expected = header.group(1), body_hash(body)
        if actual != expected:
            failures.append(
                "stale header hash.\n    header:   %s\n    expected: %s\n"
                "  Code Ocean will reuse the cached image -- Dockerfile edits will\n"
                "  NOT deploy -- until this is corrected."
                % (actual.decode(), expected.decode())
            )
    if post_digest is not None:
        idx = marker_index(body)
        if idx is None:
            failures.append(
                "no '# postInstall-sha256:' line in the Dockerfile body. Without it,\n"
                "  editing environment/postInstall does not change the Dockerfile and\n"
                "  Code Ocean may not rebuild the environment."
            )
        elif MARKER_RE.match(body[idx]).group(1) != post_digest:
            failures.append(
                "postInstall digest is stale.\n    recorded: %s\n    actual:   %s\n"
                "  environment/postInstall changed but the Dockerfile did not, so the\n"
                "  cached image would be reused."
                % (MARKER_RE.match(body[idx]).group(1).decode(), post_digest.decode())
            )
    if failures:
        for f in failures:
            sys.stderr.write("%s: %s\n" % (rel, f))
        sys.stderr.write("  Run: make capsule-fix\n")
        raise SystemExit(1)
    print("%s: hash OK" % rel)
    raise SystemExit(0)

# mode == "fix"
old_header = header.group(1).decode() if header else "(none)"
notes = []

if post_digest is not None:
    idx = marker_index(body)
    new_marker = marker_line(post_digest)
    if idx is None:
        insert_at = next(
            (i for i, ln in enumerate(body) if ln.startswith(b"COPY postInstall")), 0
        )
        body.insert(insert_at, new_marker)
        notes.append("inserted postInstall digest")
    elif body[idx] != new_marker:
        body[idx] = new_marker
        notes.append("refreshed postInstall digest")

new_header = body_hash(body)
out = [b"# hash:sha256:" + new_header + b"\n"] + body

directory = os.path.dirname(path) or "."
fd, tmp = tempfile.mkstemp(dir=directory, prefix=".co_env_hash.")
try:
    with os.fdopen(fd, "wb") as fh:
        fh.writelines(out)
    shutil.copymode(path, tmp)
    os.replace(tmp, path)
except BaseException:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise

suffix = (" (%s)" % ", ".join(notes)) if notes else ""
if old_header == new_header.decode():
    print("%s: hash already correct %s%s" % (rel, new_header.decode(), suffix))
else:
    print("%s: hash updated %s -> %s%s" % (rel, old_header, new_header.decode(), suffix))
PY
