# Step 1: Initial Search

Performs the initial PubMed literature search based on a research question.
Uses an LLM to generate query strings and iteratively refines them until
enough articles are found.

**Input:** Research question (string)

**Output:** Excel file with article metadata (base64-encoded XLSX)

## Manager

::: ScopingReview.InitialSearch.Manager
    options:
      members:
        - BaseSearchManager
        - FastAPISearchManager

## Workflow

::: ScopingReview.InitialSearch.Workflow
    options:
      members:
        - CustomPubMedQueryGenerator
        - ArticleSearch
