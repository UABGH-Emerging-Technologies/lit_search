# Step 2b: Iterative Search

Refines the PubMed search using keywords from Step 2a. Builds an enriched
query prompt incorporating primary, secondary, and exclusion keywords, then
merges new results with the original article set.

**Input:** Article DataFrame + keyword lists from Step 2a

**Output:** Merged, deduplicated article DataFrame (base64-encoded XLSX)

## Manager

::: ScopingReview.IterateSearch.Manager

## Workflow

::: ScopingReview.IterateSearch.Workflow
