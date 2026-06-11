# Step 5: Draft Generation

Generates a complete first draft of the scoping review from the category
summaries. Produces an introduction, conclusion, and abstract via separate
LLM calls, then assembles them with a boilerplate methodology section and
the original results.

**Input:** Markdown string of category summaries from Step 4

**Output:** Complete draft document (base64-encoded DOCX)

## Manager

::: ScopingReview.Draft.Manager
    options:
      members:
        - DraftReviewManager

## Workflow

::: ScopingReview.Draft.Workflow
