# Plan: Parallel LLM Calls via LangChain `ainvoke`

## Summary

Introduce async parallel LLM invocations (bounded to 5 concurrent calls) in the
scoping review pipeline steps where independent per-article LLM calls are
currently executed sequentially.  This targets **Step 3 (Categorize)** and
**Step 4 (Summarize)**, which iterate over articles one-by-one despite having no
data dependency between individual article calls.

---

## Analysis

### Current LLM Call Patterns

| Step | Route | Pattern | Calls | Independent? |
|------|-------|---------|-------|-------------|
| Step 1 (Search) | `/step1` | Iterative query refinement loop | 1-N | No - each uses previous result |
| Step 2A (Keywords) | `/step2/keywords` | Single call | 1 | N/A |
| Step 2B (Iteration) | `/step2/iteration` | Delegates to Step 1 loop | 1-N | No |
| **Step 3 (Categorize)** | `/step3` | `for row in df.iterrows()` | M (per article) | **Yes** |
| **Step 4 (Summarize)** | `/step4` | category -> article -> chunk loops | K x C x N | **Partially** (articles independent; chunks dependent) |
| Step 5 (Draft) | `/step5` | Intro -> Conclusion -> Abstract | 3 | No - strict chain |
| Standalone Summary | `/summary` | Search + single summary | 1-N + 1 | No |
| Bibliography | `/bibliography` | No LLM calls | 0 | N/A |

### Parallelization Targets

**Step 3 - Article Categorization** (`ScopingReview/Categorize/Workflow.py:48-64`)
- Current: sequential `for index, row in reduced_df.iterrows()` with one LLM
  call per article
- Each article's categorization is fully independent (receives its own
  abstract+title, returns its own categories)
- Expected speedup: ~6x for 30 articles (6 batches of 5)

**Step 4 - Article Summarization** (`ScopingReview/Summarize/Workflow.py:116-171`)
- Current: nested loop `for category` -> `for article` -> `for chunk`
- Article-level summaries within a category are independent of each other
- Chunk refinement within a single article is **dependent** (each refines
  the previous summary) and must stay sequential
- Category-level summaries can also run in parallel once their article summaries
  are complete
- Expected speedup: ~5x on the article dimension within each category

### Not Parallelizable

- **Step 5 (Draft)**: Intro -> Conclusion (needs intro) -> Abstract (needs both).
  Strict data dependency chain.
- **Step 1/2B (Search)**: Each PubMed query iteration depends on whether the
  previous query found sufficient articles.
- **Step 2A (Keywords)**: Single LLM call.

---

## Implementation Plan

### 1. Add async LLM path in `aiweb_common`

**File: `aiweb_common/generate/QueryInterface.py`**
- Add `async_generate_langchain_response(assembled_prompt)` method
- Uses `self.language_model_interface.ainvoke(assembled_prompt)` instead of
  `.invoke()`
- Wraps in `get_openai_callback()` for cost tracking (works with `ainvoke`)

**File: `aiweb_common/generate/SingleResponse.py`** (and `SingleResponseServicer`)
- Add `async_generate_response(assembled_prompt)` that delegates to the new
  async method

### 2. Parallelize Step 3 - Categorize

**File: `ScopingReview/Categorize/Workflow.py`**

Replace the sequential loop:
```python
# BEFORE
for index, row in reduced_df.iterrows():
    ...
    response, response_meta = self.single_response.generate_response(assembled_prompt)
    ...
```

With semaphore-bounded async gather:
```python
# AFTER
import asyncio

async def categorize_articles(self):
    reduced_df = self._prep_df_for_categorization()
    input_list = self._prep_categorylist()
    semaphore = asyncio.Semaphore(5)

    async def _categorize_one(index, row):
        async with semaphore:
            data = row[["abstract", "title"]]
            assembled_prompt = ...  # same prompt assembly
            response, response_meta = await self.single_response.async_generate_response(assembled_prompt)
            self._update_total_cost(response_meta)
            return index, extract_response_text(response.content).replace("'", "").lower()

    tasks = [_categorize_one(idx, row) for idx, row in reduced_df.iterrows()]
    results = await asyncio.gather(*tasks)

    for index, category in results:
        reduced_df.loc[index, "category"] = category
    ...
```

### 3. Parallelize Step 4 - Summarize

**File: `ScopingReview/Summarize/Workflow.py`**

Within `summarize_all_categories()`, parallelize the **article** dimension:
```python
# For each category, run article summaries in parallel
async def _summarize_one_article(self, row, semaphore):
    async with semaphore:
        return await self.async_summarize_article_in_chunks(row.Text)
```

The chunk-level refinement within `summarize_article_in_chunks` stays sequential
(each chunk refines the previous summary), but uses `ainvoke` for each call.

Category-level summaries can also run in parallel via `asyncio.gather` since
they are independent.

### 4. Update FastAPI endpoints

**Files: `app/v01/scoping/step3.py`, `app/v01/scoping/step4.py`**

The endpoints are already `async def`. Change the workflow `.process()` calls
from synchronous to `await workflow.async_process()` (or rename).

### 5. Thread-safe cost tracking

`_update_total_cost()` does `self.total_cost += response_meta.total_cost`.
With concurrent coroutines on a single event loop this is safe (no preemption
between awaits), but add a note/comment for clarity.

---

## Files to Modify

| File | Change |
|------|--------|
| `aiweb_common/generate/QueryInterface.py` | Add `async_generate_langchain_response()` |
| `aiweb_common/generate/SingleResponseServicer.py` | Add async method |
| `aiweb_common/generate/SingleResponse.py` | Add `async_generate_response()` |
| `ScopingReview/Categorize/Workflow.py` | Async `categorize_articles()` with `asyncio.gather` + `Semaphore(5)` |
| `ScopingReview/Summarize/Workflow.py` | Async article summarization with `asyncio.gather` + `Semaphore(5)` |
| `app/v01/scoping/step3.py` | `await` the async workflow |
| `app/v01/scoping/step4.py` | `await` the async workflow |

## Risks & Mitigations

- **Rate limiting**: The `Semaphore(5)` bounds concurrency; adjust if the
  upstream API has a lower rate limit.
- **Error handling**: `asyncio.gather` with `return_exceptions=True` can
  collect errors without aborting all tasks; decide on fail-fast vs.
  best-effort per step.
- **Cost tracking**: Safe within a single asyncio event loop (GIL + cooperative
  scheduling), but verify with load testing.
- **`get_openai_callback()` with `ainvoke`**: Supported in LangChain >=0.1;
  current dependency (`langchain-core==1.2.28`) is well past this.
