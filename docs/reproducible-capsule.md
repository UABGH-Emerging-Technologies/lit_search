# Reproducible Capsule

This repository is shaped as a [Code Ocean](https://codeocean.com) capsule. Code Ocean maps the
repo's `code/`, `data/`, `environment/` and `metadata/` folders onto the capsule's corresponding
directories, and executes `code/run` as the entry point.

`code/run` does not start a server. It runs `code/scripts/capsule_driver.py`, which drives all six
pipeline steps in-process through FastAPI's `TestClient` and writes every artifact to `/results`.

## Two modes

| Mode | Credentials | Network | Used when |
|------|-------------|---------|-----------|
| `demo` (default) | none | none | Published capsule, Reproducible Runs, CI |
| `live` | LLM + NCBI + LibKey | yes | Maintainers running the real pipeline |

Select with `--mode {auto,demo,live}` or the `LIT_RUN_MODE` environment variable. The default,
`auto`, chooses `live` only when a complete credential set is present, and `demo` otherwise — so a
capsule with no secrets attached always reproduces.

```bash
cd code
./run                      # auto: demo unless credentials are present
./run --mode demo          # force offline replay
./run --check-env          # validate prerequisites for the resolved mode
```

## Synthetic screening (read this before citing any output)

A real scoping review screens articles with **two human reviewers**.
`BaseManager.make_initial_df` writes `Author 1/2: Relevant Article? (Yes/No)`
columns defaulted to `No`; a researcher marks the keepers and re-uploads the
workbook, and `BaseManager._check_relevance` treats a `Yes` from either reviewer
as relevant.

The capsule runs all six steps unattended, so nobody marks anything. Left alone,
every row stays `No`, `get_relevant_rows()` returns an empty frame, step 3's
categorization loop iterates zero times, the `category` column is never created,
and step 4 fails with `KeyError: 'category'`.

Demo and recording runs therefore mark the first N articles relevant
automatically (`--auto-screen N`, `LIT_AUTO_SCREEN`, default 15; `0` disables).
**These are not real screening decisions.** Every run that uses it writes a
`DEMO_NOTICE.txt` into the results directory and a `"screening"` block into
`run_manifest.json`. Live runs default to `0`, because a real run should carry
real reviewer decisions in the uploaded workbook.

The capsule demonstrates pipeline mechanics. Its outputs are not a scoping
review result and must not be read as one.

## How demo mode works

The pipeline reaches the network in exactly three places, all inside `aiweb_common`:

1. `llm_interface.invoke()` — every workflow builds `SingleResponseHandler(self.llm_interface)`,
   landing in `QueryInterface.generate_langchain_response`.
2. `PubMedInterface.search_pubmed_articles` / `fetch_article_details` (Entrez).
3. `PubMedInterface.fetch_full_text` (PMC + LibKey).

`code/capsule/replay.py` doubles all three. In demo mode it serves recorded responses keyed by a
SHA-256 of the canonical prompt text, then installs a network guard and counts every interception.
A clean demo run reports `"blocked_network_calls": 0` in `run_manifest.json` — a non-zero value
means something tried to reach out.

The guard blocks `socket.socket.connect`/`connect_ex` plus `socket.getaddrinfo`,
`socket.create_connection` and `socket.gethostbyname` — deliberately *not* the `socket`
constructor. Blocking construction also breaks `socket.socketpair()`, which asyncio uses for the
event loop's self-pipe, taking down `TestClient` itself instead of catching a network call.
Connecting and resolving are what actually reach the network. `getaddrinfo` needs its own patch
because `app/v01/net_validators.py` calls it directly on every request.

A cassette miss is a hard failure, never a silent fallback. Replay keys on exact prompt text, so
changing a prompt template, a workflow's call sequence, or the demo research question invalidates
the fixtures and requires re-recording.

### Prompts must be deterministic

Keying on prompt text imposes a real constraint: **the same inputs must produce the same prompt
bytes every run.** Anything varying — a timestamp, a `set` iteration order, or a LangChain response
object interpolated into a later prompt — makes replay impossible.

That last one was a live bug. `Draft/Workflow.write_first_draft` passed the raw `AIMessage` for the
introduction into the conclusion and abstract prompts. Python stringified it, embedding
`additional_kwargs={} response_metadata={} id='lc_run--<random uuid>'`, so those prompts differed on
every run. It also meant live runs sent LangChain object repr to the model instead of the drafted
text. Always interpolate `extract_response_text(response.content)`, never the response object.

`tests/test_capsule_pipeline_offline.py` guards this: it runs the whole pipeline twice against fake
externals and asserts every prompt is byte-identical, plus asserts no prompt contains a message
repr. Both catch the regression if it returns.

### Why the fixtures live in `code/`, not `data/`

Code Ocean provisions `/data` from attached Data Assets, not from the git repository — which is why
`.gitignore` excludes `data/`. Fixtures kept there would not travel with a published capsule, and a
capsule that depends on an attached asset is not self-contained. They ship in
`code/demo_fixtures/` instead. Override the location with `LIT_DEMO_FIXTURES`.

## Re-recording the fixtures

Run once, locally, with real credentials in the environment:

```bash
cd code
python scripts/record_demo.py
```

This executes the same `_run_pipeline` code path the capsule uses, with recording doubles wrapped
around the three seams, and writes `llm.json`, `pubmed_search.json`, `pubmed_details.json`,
`pubmed_fulltext.json` and `fixtures.json` to `code/demo_fixtures/`.

Only prompt text and response content are captured — never request headers, `Authorization`
values, or API keys. The recorder finishes with a scrub pass and **fails the recording** if
anything secret-shaped slipped in. Review the fixtures by hand before committing them.

Recording makes several hundred LLM calls (`Categorize` iterates per article up to
`MAX_ARTICLES_SR`, `Summarize` iterates per text chunk and per category), so budget accordingly.

**Recording resumes by default.** Every captured call is written to disk even when the run fails
part way, and a re-run reuses anything already recorded instead of paying for it again. Keys are
prompt hashes, so a changed prompt still misses and goes live — resume cannot serve you a stale
answer. Pass `--fresh` to ignore existing fixtures and re-request everything. A partial recording
is marked `"complete": false` in `fixtures.json`.

## A note on output hashes

`run_manifest.json` records a `sha256` per output file. **These are not stable across runs.** XLSX
files are written by `xlsxwriter`, which stamps `dcterms:created` with the current time when no
document properties are set, and DOCX files are produced by the `pandoc` binary via `pypandoc`,
which does the same. Both formats are zip containers whose entry timestamps also move.

Treat the raw-byte digests as per-run integrity values. Demo mode is deterministic in *content* —
the same fixtures produce the same review — not in bytes.

## Environment gotchas

Two invariants are enforced by `make capsule-check`, and both will silently ship a stale image if
ignored:

- `environment/Dockerfile` carries its own cache key on line 1 as `# hash:sha256:<digest of lines
  2..EOF>`, plus a `# postInstall-sha256:` marker. Code Ocean rebuilds only when the header
  changes, so a hand-edited Dockerfile or postInstall with a stale header is ignored. Run
  `make capsule-fix` after editing either file.
- `environment/postInstall` embeds a verbatim copy of `code/requirements.txt`, because `/code` does
  not exist at environment build time.

`postInstall` also pre-downloads tiktoken's `gpt2` encoding into `/opt/tiktoken-cache`.
`Summarize/Workflow.py` calls `RecursiveCharacterTextSplitter.from_tiktoken_encoder()` without a
`model_name`, which resolves that default encoding — and tiktoken fetches it over HTTP on first
use. Baking it in keeps the demo run network-free and stops the live run from reaching out
mid-pipeline. `TIKTOKEN_CACHE_DIR` must stay set at runtime.

## Verifying offline reproduction

The strongest check is to cut the network rather than trust the guard:

```bash
cd code
unshare -rn env RESULTS_DIR=/tmp/lit-demo ./run --mode demo
```

Expect exit code 0, six artifacts plus `run_manifest.json` in `/tmp/lit-demo`, and a manifest
reporting `"mode": "demo"`, `"status": "succeeded"`, `"blocked_network_calls": 0`.

## Secret gates

Two stdlib-only checks run in CI (`.github/workflows/security-scan.yml`) and locally via
`make scan-secrets`:

- `tools/scan_secrets.py` scans the **content** of every tracked file. It is a content gate, not a
  filename gate: a `git filter-repo --replace-text` mapping — whose left-hand sides are the literal
  secrets — was once committed under the obvious name `purge_secrets_history.sh` and passed a
  review that only checked staged paths.
- `code/capsule/scrub.py` scans the recorded demo fixtures, and `record_demo.py` runs it inline so a
  recording that captured something secret-shaped fails instead of being committed.

The scanner deliberately holds **no secret values** — it runs in public CI, so anything in it would
be published. It matches on provider formats, credential context, and entropy instead. Legitimate
long hex in this repo (cassette prompt hashes, manifest digests, the Dockerfile cache key, pinned
git SHAs, a gist id in a comment) is excluded by requiring a credential keyword on the same line and
rejecting values that are plainly identifier names. Mark a deliberate test fixture with
`pragma: allowlist secret` on its line.

`code/tests/test_scan_secrets.py` covers both directions — the formats it must catch and the
repo content it must ignore — because a detector that quietly stops detecting is worse than none.

