# Scoping Workflow Overview

The scoping review pipeline consists of five sequential steps, each building on the
output of the previous one:

1. **[Step 1 -- Initial Search](step1.md)**: Generate a PubMed query from a research
   question and retrieve an initial set of articles.

2. **[Step 2a -- Keyword Extraction](step2-keywords.md)**: Extract primary, secondary,
   and exclusion keywords from the initial article set.

3. **[Step 2b -- Iterative Search](step2-iteration.md)**: Refine the PubMed query
   using extracted keywords and merge new results with the initial set.

4. **[Step 3 -- Categorization](step3.md)**: Assign user-defined categories to each
   article using an LLM and fetch full text where available.

5. **[Step 4 -- Summarization](step4.md)**: Summarize articles within each category,
   producing a per-category narrative with APA citations.

6. **[Step 5 -- Draft Generation](step5.md)**: Generate a complete first draft of the
   scoping review with introduction, methodology, results, conclusion, and abstract.

## Data Flow

```
Research Question
       |
   [Step 1] --> XLSX (articles + relevance columns)
       |
   [Step 2a] --> JSON (keyword lists)
       |
   [Step 2b] --> XLSX (merged, deduplicated articles)
       |
   [Step 3] --> XLSX (articles + categories + full text)
       |
   [Step 4] --> DOCX (category summaries)
       |
   [Step 5] --> DOCX (first draft)
```
