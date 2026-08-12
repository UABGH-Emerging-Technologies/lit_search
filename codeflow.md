# Code Flow — Scoping Review

How a research question travels through the scoping-review backend, what logic each
step applies, and how reference lists end up alphabetically ordered.

This service is the backend for the literature module of the main site
(`aiweb_interface/literature/`). The React UI calls these endpoints and renders
what they return — it computes nothing about the review itself, including
reference order.

---

## 1. The shape of the service

**Every endpoint is stateless.** No session, no database, no server-side record of
your review. The base64-encoded file returned by each step *is* the state, and you
hand it back to the next step.

That explains the "two ways" the tool gets used:

| Mode | What happens |
|---|---|
| **Chained** | The React app holds the base64 string in memory and posts it straight to the next endpoint. |
| **Download / resume** | You download the file, edit it in Excel, come back later, upload it. |

**These are the same code path.** The backend receives identical bytes either way
and cannot tell them apart. Nothing behaves differently between them.

**Credentials are per-request.** Every LLM-calling endpoint requires
`openai_compatible_endpoint` and `openai_compatible_model` in the JSON body and
`Authorization: Bearer <key>` in the header. No server-side defaults — the LLM
client is built fresh per request.

## 2. Endpoint map

| Route | In | Out |
|---|---|---|
| `POST /v01/scoping/step1/` | research question | XLSX (candidate papers) |
| `POST /v01/scoping/step2/keywords/` | XLSX + question | JSON (3 keyword lists) |
| `POST /v01/scoping/step2/iteration/` | XLSX + keywords | XLSX (expanded set) |
| `POST /v01/scoping/step3/` | XLSX + categories | XLSX (+ category, full text) |
| `POST /v01/scoping/step4/` | XLSX + question | DOCX (summaries per category) |
| `POST /v01/scoping/step5/` | DOCX + question | DOCX (draft review) |
| `POST /v01/standalone/summary/` | research question | DOCX (one-shot summary) |
| `POST /v01/standalone/bibliography/` | citations / PMIDs | BIB (BibTeX) |

## 3. The three layers

```
Router          app/v01/scoping/stepN.py
                  base64 -> DataFrame, reads credentials, maps errors to HTTP codes
      |
Workflow        ScopingReview/<Feature>/Workflow.py
                  the logic: builds prompts, calls the LLM, assembles output
      |
Manager         ScopingReview/<Feature>/Manager.py
                  file I/O, DataFrame shaping, PubMed/LibKey calls
```

Managers inherit `ScopingReview/BaseManager.py` (`make_initial_df`,
`write_excel_output`, `get_encoded_excel`, `get_encoded_docx`, `fetch_full_text`,
`_check_relevance`). Workflows inherit `aiweb_common.WorkflowHandler` from the
separate `llm_utils` package (`_init_openai`, cost tracking).

---

## 4. Worked example

> **Research question:** *What are the risk factors for postoperative delirium in
> elderly surgical patients?*

### Step 1 — Initial search

`POST /v01/scoping/step1/` → `ArticleSearch.process()`
(`ScopingReview/InitialSearch/Workflow.py:59`)

**Logic: LLM-generated query with a widen-and-retry loop.**

1. `CustomPubMedQueryGenerator` turns the question into a real PubMed boolean query:

   ```
   ("postoperative delirium"[MeSH] OR "delirium"[tiab]) AND ("aged"[MeSH] OR elderly[tiab])
   AND ("risk factors"[MeSH] OR predictor*[tiab]) AND ("surgery"[MeSH])
   ```

2. `search_pubmed_articles` runs it through Entrez with `sort="relevance"` and
   `retmax=200` (`config.MAX_ARTICLES_SR`). **Results come back in PubMed
   relevance order** — the reason reference lists needed sorting at all.

3. **The retry rule:** if a query returns ≤ 10 IDs (`config.MIN_ARTICLES`), the
   LLM is asked to broaden it and the search reruns — up to 6 attempts
   (`config.MAX_TRIES`). Each attempt is passed the previous query
   (`process(loop_n=n, last_query=search_string)`), so it refines rather than
   restarting.

   After 6 failures the code returns a hard-coded one-row **fallback DataFrame**
   (`InitialSearch/Workflow.py:93`) instead of `None`, so downstream steps don't
   crash. It contains fake data — a downstream success is not proof the search
   worked.

4. `fetch_article_details` builds one row per article:

   ```
   date_published   "2020 Oct"
   title            "Postoperative delirium: perioperative assessment..."
   keywords         ["delirium", "aged", "hip fractures"]
   abstract         "BACKGROUND: Postoperative delirium is..."
   pmid             "32798069"
   authors          ["Jin Z", "Hu J", "Ma D"]        <-- a Python list
   journal          "British journal of anaesthesia"
   citation         "Jin, Z., Hu, J., Ma, D. (2020 Oct). Postoperative delirium...
                     British journal of anaesthesia, 125, 492-504. PMID: 32798069"
   ```

   `citation` is assembled upstream in
   `llm_utils/aiweb_common/resource/PubMedInterface.py:85` and **always begins
   with the first author's surname** in APA form. That property is what makes
   citation-string sorting work at step 5.

5. `make_initial_df` (`BaseManager.py:340`) inserts the two reviewer columns at
   the front, both defaulting to `"No"`, and renames `pmid` → `PMID`.

6. `write_excel_output` writes Sheet1 (papers) and Sheet2 (search terms); the file
   is base64-encoded and returned.

**→ Human step.** Two reviewers mark `Yes` on papers worth keeping.

> **What the Excel trip does to `authors`:** it was a Python list. Excel has no
> list type, so pandas writes its `repr` — the cell reads
> `['Jin Z', 'Hu J', 'Ma D']` — and reads back a *string*. Every later consumer
> must handle both a real list and that string. This is why
> `first_author_surname` uses `ast.literal_eval`.

### Step 2a — Keyword extraction

`POST /v01/scoping/step2/keywords/` → `KeywordWorkflow.process()`
(`ScopingReview/Keywords/Workflow.py:52`)

**Logic: filter to accepted papers, count keyword frequency, ask the LLM once.**

1. `get_relevant_rows` (`BaseManager.py:389`) applies `_check_relevance` per row:
   if **either** reviewer column reads yes / y / true / t → `Relevant = "True"`,
   else `None`. Rows with `None` are dropped via `dropna(subset=["Relevant"])`.
   **One reviewer's Yes is enough** — it is an OR, not an AND.
2. Keywords across kept rows are counted and rendered as
   `"delirium x14, aged x11, hip fractures x3"`, so the LLM sees which terms
   actually dominate the accepted set.
3. One LLM call returns JSON; `parse_keywords` pulls it out with a regex
   (`\{.*?\}`, DOTALL) and `json.loads`:

   ```json
   { "Primary Keywords":   ["postoperative delirium", "elderly"],
     "Secondary Keywords": ["risk factors", "hip fracture", "anesthesia depth"],
     "Exclusion Keywords": ["pediatric", "ICU delirium"] }
   ```

   If the JSON is malformed, it returns three empty lists rather than raising.

**→ Human step.** You edit the three lists in the UI.

### Step 2b — Iteration

`POST /v01/scoping/step2/iteration/` → `IterateSearch.process()`
(`ScopingReview/IterateSearch/Workflow.py:45`)

**Logic: re-search with the keywords, then merge so human decisions always win.**

1. `_prepare_query_with_keywords` builds a natural-language prompt from the
   research question plus the three lists (include / also-include / exclude).
2. That prompt drives a fresh `ArticleSearch` — same retry rule as step 1.
3. The merge:

   ```python
   combined = pd.concat([selected, articles_df], ignore_index=True)
   combined.drop_duplicates(subset="PMID", keep="first", inplace=True)
   ```

   `selected` (your Yes papers) is concatenated **first**, so `keep="first"` means
   the reviewed copy of a paper beats the freshly-fetched copy. Your Yes/No
   answers are never overwritten.

4. Returns a new XLSX. 2a → 2b can be repeated as often as you like.

> After this merge `authors` is **mixed-type**: rows carried from the upload hold
> repr strings, freshly-fetched rows hold real lists. Consumers must tolerate both
> in one column.

### Step 3 — Categorisation

`POST /v01/scoping/step3/` → `CategorizeWorkflow.process()`
(`ScopingReview/Categorize/Workflow.py:84`)

**Logic: one LLM call per article, against your category list.**

1. Filter to relevant rows only.
2. For each article, title + abstract + your categories go to the LLM; the reply
   is lowercased and stored as a comma-joined string. An article may receive
   several: `category = "surgical risk, patient comorbidity"`.
   **Cost scales linearly** — 200 articles is 200 calls.
3. `fetch_full_text` tries PMC, then LibKey, per PMID. Results merge on `PMID`,
   adding `URL`, `Downloaded`, `Text`. Missing full text →
   `Text = "Text not available"`.
4. Returns an XLSX with the new columns.

### Step 4 — Summarisation

`POST /v01/scoping/step4/` → `SummarizeArticles.summarize_all_categories()`
(`ScopingReview/Summarize/Workflow.py:120`)

**Logic: explode by category, summarise each article, then synthesise per
category.**

1. `categories_limit_check` splits `category` into a list and flags any category
   above 60 articles (`config.SUBCLASS_THRESHOLD`). The warning is returned in the
   `Warning` response header (`app/v01/scoping/step4.py:68`); it does not block.
2. `Text` falls back to `abstract` where full text is missing; rows with neither
   are dropped.
3. `df.explode("category")` → one row per (article, category) pair. **An article
   in two categories now occupies two rows.** This is what creates duplicate
   citations later.
4. Per category:
   - Each article is summarised on its own. Long text is chunked at 13 000 tokens
     with 1 000 overlap and summarised **progressively** — summarise chunk 1, then
     refine that summary with chunk 2, and so on (`summarize_article_in_chunks`).
   - All article summaries are concatenated into one category-synthesis prompt.
   - Output is `# <category>` + synthesis + that category's reference block.
5. Markdown → DOCX via pypandoc.

**Where the sort happens:** at the render point only —
`"\n\n".join(sort_reference_df(filtered_rows).citation)`
(`Summarize/Workflow.py:175`). It is deliberately *not* applied before the
summarisation loop, because that would reorder the summaries fed into the
synthesis prompt and change the generated prose.

### Step 5 — Draft review

`POST /v01/scoping/step5/` → `DraftReview.write_first_draft()`
(`ScopingReview/Draft/Workflow.py:80`)

**Logic: partition the step-4 document into prose vs references, then write three
sections from the prose.**

The step-4 DOCX arrives as plain text. **There is no DataFrame here** — this is
why step 5 needs its own sorting mechanism.

1. `extract_apa_citations` (`ScopingReview/Draft/Manager.py:24`) splits the
   document and partitions on a single test:

   ```python
   paragraphs = [para.strip() for para in markdown_text.split("\n") if para.strip()]
   citations     = [p for p in paragraphs if "PMID" in p]
   non_citations = [p for p in paragraphs if "PMID" not in p]
   ```

   **The split is on `"\n"`, not `"\n\n"`, and that matters.** Step 4 writes the
   DOCX with pypandoc, which emits one Word paragraph per markdown block and no
   blank ones between. Step 5 reads it back with
   `FastAPIUploadManager.process_file_bytes`
   (`llm_utils/aiweb_common/file_operations/upload_manager.py:141`), which joins
   paragraphs with a **single** `"\n"`. So `"\n\n"` never occurs: splitting on it
   collapsed the entire document into one paragraph, which contained "PMID", so
   `citations` was `[whole document]` and `non_citations` was `[]` — an empty
   Results section and three LLM sections written from no source material at all.
   Splitting on `"\n"` restores one entry per original paragraph; blank entries
   are dropped so blank-line-separated input still works.

2. `sort_citation_paragraphs(citations)` de-duplicates and alphabetises — see §5.
3. Three sequential LLM calls, each fed the previous output:
   **Introduction → Conclusion → Abstract**. All three read `non_citations` only,
   in original document order.
4. `assemble_document` concatenates, with no LLM pass over the middle:

   ```
   Abstract | Introduction | Methods (boilerplate.METHODOLOGY, verbatim)
   | Results/Discussion (non_citations) | Conclusion | References (sorted, deduped)
   ```

   Because `METHODOLOGY` is inserted verbatim, anything in that constant reaches
   the deliverable character-for-character.

### Standalone summary

`POST /v01/standalone/summary/` → `StandaloneSummary.process()`
(`ScopingReview/Standalone/Workflow.py:88`) collapses steps 1 and 4: search
PubMed, summarise all abstracts in one call, emit a DOCX with a "Works consulted"
list.

Note the ordering: the summary is generated **before** `format_response` sorts the
frame, so sorting affects only the displayed list, never the prose.

### Bibliography

`POST /v01/standalone/bibliography/` is a **separate path** sharing nothing with
the above. It pulls PMIDs from the upload, re-fetches XML from Entrez, and emits
BibTeX in PubMed's response order.

---

## 5. Reference sorting — the logic

All of it lives in `ScopingReview/reference_sort.py`. There are **two entry
points** because references exist in two different forms.

### Why sorting is safe

In-text citations in the generated prose are **author-date** — `(Jin et al.,
2020)` — so a reference's position in the list carries no meaning and reordering
is purely presentational. Under a numbered (Vancouver) style, position maps to
in-text markers and reordering would corrupt the document.
`ScopingReview_config/config.py` holds `SORT_REFERENCES = True` as the kill switch
for exactly that scenario. Both entry points check it.

### Entry point A — `sort_reference_df(df)` (`reference_sort.py:106`)

Used where a DataFrame exists: **step 4** per category, and the **standalone
summary**.

**Sort key: first-author surname → publication year → title.** Implemented by
assigning three temporary columns, `sort_values(kind="stable")`, then dropping
them.

- **`first_author_surname(authors)`** (`:50`) — takes the first author and returns
  the surname.
  - Accepts three shapes: a real list (`["Jin Z", "Hu J"]`), the repr of a list
    after an Excel round trip (`"['Jin Z', 'Hu J']"`, parsed with
    `ast.literal_eval`), or a plain string.
  - PubMed's `AU` format is `"Surname Initials"`, so the surname is
    `first.rsplit(" ", 1)[0]`. This deliberately mirrors `_format_authors` in
    `llm_utils/aiweb_common/resource/PubMedInterface.py:29`, which uses the same
    `rsplit` to build the citation — so the sort key and the rendered text agree.
  - `rsplit` keeps multi-word surnames whole: `"van der Mast RC"` → `van der mast`,
    filing under **V**, which is what most reference managers do.
  - Returns `""` for `None`, empty, `"nan"`, or an empty list. Empty keys sort
    together at the top rather than raising.
- **`publication_year(value)`** (`:92`) — first four-digit run in the date, else
  `0`. The field is not a fixed format: `"2020 Oct"`, `"2018"`, `"1999 Sep-Oct"`,
  `"2025 Autumn"`, `"2020 Oct 23"` all occur.
- Returns the frame unchanged if it is empty or has no `authors` column, so the
  step 1 fallback frame passes through untouched.

### Entry point B — `sort_citation_paragraphs(citations)` (`reference_sort.py:147`)

Used at **step 5**, where there is no DataFrame — only rendered citation strings
recovered from the document.

**Two operations, in order:**

1. **De-duplicate**, keeping the first occurrence. Key is the PMID matched by
   `PMID:\s*(\d+)`, falling back to the normalized full text when absent. This is
   necessary because step 4 exploded on category, so an article filed under two
   categories was cited in both blocks and arrives here twice.
2. **Sort by `normalize_sort_text(paragraph)`** — the whole citation string —
   with a stable sort.

Sorting the rendered string works because `_format_apa_citation` always puts the
first author's surname first. It also gives correct APA multi-author ordering for
free: co-author names sit between the surname and the year, so two papers by the
same first author break ties on the second author, which is what APA specifies.

### Shared normalisation — `normalize_sort_text(value)` (`reference_sort.py:30`)

`unicodedata.normalize("NFKD", …)`, drop combining marks, `casefold()`.

Deliberately **not** `locale.strxfrm`: a real locale must be compiled into the
image and this container ships C/POSIX only, so `strxfrm` would silently degrade
to byte ordering — the exact failure the sort exists to prevent. PubMed already
delivers surnames ASCII-folded (`Muller`, `Jarvela`), so this yields the same
ordering with no runtime dependency.

### Failure behaviour

Both functions are wrapped so they **never raise**. An unsortable input returns
unchanged with a printed note. Ordering is presentational; it is not worth failing
a request that has already spent hundreds of LLM calls.

The `config` import inside both functions is lazy and `try`-guarded on purpose —
`ScopingReview_config.config` imports `app_config`, which imports `aiweb_common`,
so a top-level import would make this module untestable without the full
dependency tree.

### Ordering, end to end

| Where | Source | Key | Scope |
|---|---|---|---|
| Step 4, per category | DataFrame `citation` column | surname → year → title | A–Z inside each category block |
| Step 5, `# References` | citation paragraphs | whole citation string | A–Z across the document, de-duplicated |
| Standalone summary | DataFrame `citation` column | surname → year → title | A–Z across the list |
| Bibliography `.bib` | PubMed XML | none | PubMed response order |

The two keys differ slightly: for two papers by the same first author, step 5
breaks the tie on co-author names (APA-correct) while step 4 breaks it on year.

### Worked ordering example

Step 4 produced two category blocks, each already A–Z, with one article filed
under both:

```
# surgical risk
Williams, A., Ng, P. (2021 Mar). … PMID: 33111222
Jin, Z., Hu, J., Ma, D. (2020 Oct). … PMID: 32812345

# patient comorbidity
Jin, Z., Hu, J., Ma, D. (2020 Oct). … PMID: 32812345      <-- same article again
Adams, B. (2019 Jan). … PMID: 30555111
```

Step 5 flattens both blocks into one list — alphabetical in runs, scrambled
overall, with a duplicate. `sort_citation_paragraphs` drops the repeated PMID and
orders the survivors:

```
# References
Adams, B. (2019 Jan). … PMID: 30555111
Jin, Z., Hu, J., Ma, D. (2020 Oct). … PMID: 32812345
Williams, A., Ng, P. (2021 Mar). … PMID: 33111222
```

---

## 6. Things that will bite you

- **`authors` is not one type.** Real list from PubMed, repr string after an Excel
  round trip, and both at once after the step 2b merge.
- **`Relevant` is `"True"` or `None`, not a boolean.** The filter is
  `dropna(subset=["Relevant"])`.
- **One reviewer's Yes is enough** — `_check_relevance` is an OR.
- **Step 3 costs one LLM call per article.**
- **Step 4 explodes on category**, so multi-category articles are summarised and
  cited once per category. Step 5 de-duplicates; step 4's own document does not.
- **Any paragraph containing "PMID" is a reference at step 5.** If a generated
  summary mentions a PMID inline, that paragraph leaves the prose and joins the
  reference list.
- **`boilerplate.METHODOLOGY` is inserted verbatim** — it is never paraphrased by
  an LLM despite feeding the abstract prompt as well. Anything written in that
  constant appears in the deliverable.
- **Heading levels do not survive step 4 → step 5.** `process_file_bytes` reads
  `paragraph.text` only, discarding `paragraph.style`, so `# category` returns as
  a bare word.
- **Corporate authors lose their name.** PubMed stores them in `CN`, and
  `_extract_record_data` reads only `AU` — so an AGS statement renders as
  `(2015 Feb). Title…` with no author, and sorts to the top with the other
  authorless entries.
- **The step 1 fallback frame is fake data.** Six failed attempts yield a one-row
  frame titled "Fallback Mocked Article" rather than an error.
