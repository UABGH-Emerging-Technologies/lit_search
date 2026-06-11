# Step 3: Categorization

Assigns user-defined categories to each relevant article using an LLM.
Also fetches full-text content from PMC and LibKey where available.

**Input:** Article DataFrame + comma-separated category labels

**Output:** Categorized article DataFrame with full text (base64-encoded XLSX)

## Manager

::: ScopingReview.Categorize.Manager
    options:
      members:
        - BaseCategorizeManager
        - FastAPICategorizeManager

## Workflow

::: ScopingReview.Categorize.Workflow
