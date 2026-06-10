# Lit Search Backend API

Literature Search is a two-part application. The first part allows the user to perform an initial search based on the provided research question. This is handled by the backend, which transforms the input into proper queries using a language model (LLM) and then performs a search on PubMed using the Entrez API to retrieve article IDs.

The second part of the application includes several detailed steps to refine and analyze the search results:

- **Initial Literature Search:** Perform a comprehensive search based on a research question to gather relevant articles.
- **Keyword Suggestion:** Extract and suggest keywords from search results to refine and improve search strategies.
- **Iterative Search:** Use keywords to iteratively refine search results and update article lists.
- **Article Categorization:** Organize articles into user-defined categories for easier review and analysis.
- **Summarization:** Generate concise summaries of categorized articles based on research questions.
- **Draft Review Generation:** Create draft review documents from summaries to assist in writing research papers.
- **Bibliography Conversion:** Convert bibliographic data from documents into BibTeX format for citation management.
- **Streamlit UI Integration:** Provides an interactive web interface for all workflow steps, connecting frontend inputs to backend API endpoints.

## Core Functionality

- Modular API routers for different scoping review steps and standalone features.
- Custom middleware for logging requests and handling exceptions.
- Health check endpoint to verify service status.
- Designed for extensibility and integration with literature databases and search workflows.

The backend API exposes endpoints for each of these features, while the Streamlit app offers a user-friendly interface to interact with the system.

## API Endpoints and Their Uses

### Step 1: Initial Scoping Search
**Endpoint:** `POST /v01/scoping/step1/`  
Performs an initial literature search based on a research question, compiles the results into an Excel file, and returns it for download. This is the starting point for gathering relevant articles.

### Step 2a: Keyword Suggestion
**Endpoint:** `POST /v01/scoping/step2/keywords/`  
Processes an uploaded Excel file and a research question to extract relevant keywords. Returns the extracted keywords to assist in refining the search strategy.

### Step 2b: Iterative Search with Keywords
**Endpoint:** `POST /v01/scoping/step2/iteration/`  
Accepts an Excel file, research question, and keywords to perform an iterative literature search. Returns updated search results in an Excel file, allowing refinement of the search based on keywords.

### Step 3: Article Categorization
**Endpoint:** `POST /v01/scoping/step3/`  
Categorizes articles based on user-defined categories provided along with an Excel file of articles. Returns a categorized Excel file for easier review and analysis.

### Step 4: Summarization
**Endpoint:** `POST /v01/scoping/step4/`  
Summarizes the content of articles based on a research question and an uploaded Excel file. Returns a downloadable Word document containing the summary.

### Step 5: Draft Review Generation
**Endpoint:** `POST /v01/scoping/step5/`  
Processes an uploaded Word document containing summaries and generates a draft review based on a specified research question. Returns a Word document with the draft review.

### Standalone Bibliography Conversion
**Endpoint:** `POST /v01/standalone/bibliography/`  
Converts uploaded DOCX or XLSX files containing bibliographic data (e.g., PMIDs) into a BibTeX format. Returns the BibTeX bibliography as a base64 encoded string for citation management.

### Standalone Summary Generation
**Endpoint:** `POST /v01/standalone/summary/`  
Performs an initial literature search and generates a summary based on a research question. Returns a downloadable Word document with the summarized findings.

## Streamlit UI and API Integration

The `streamlit` folder contains key files that provide the user interface and API integration for the main website:

- `streamlit/ScopingReview_api.py`: Implements the Streamlit UI for the literature search and scoping review workflow. It provides interactive pages for each step of the scoping review, including search, iteration, categorization, summarization, drafting, and bibliography generation. It manages user inputs, file uploads, and calls the backend API endpoints to perform these actions.

- `streamlit/literature_api.py`: Contains helper functions that interact with the backend API endpoints. These functions handle API requests and responses for literature search, iteration, categorization, summarization, drafting, and bibliography generation. They decode API responses and manage session state for the Streamlit app.

These files are essential for the frontend experience and connect the backend API functionality to the user-facing website.

## Running the App

This repo follows our standard microservice pattern: the backend and a scratch
Streamlit frontend come up together, and credentials are sourced from secrets
rather than typed in. Pick whichever path fits your machine — the app code is
identical for all of them.

### Default: `docker compose up` (no setup)

On any machine with the shared `/mnt/p/Secrets` mount, just run:

```bash
docker compose up --build
```

The backend (`lit_api`, port 8000) and frontend (`streamlit`, port 8501) start
together; the frontend reaches the backend over Compose's internal DNS. No
`.env`, no exported variables. Secrets are mounted as Docker secrets and read by
`aiweb_common.manage_sensitive`, which resolves `/run/secrets/<name>` first.

Open the UI at <http://localhost:8501>.

### No `/mnt/p/Secrets`? Use a `.env` (Docker)

If you don't have the mount (e.g. off-network), switch each secret to its
env-var source: in `docker-compose.yml`, comment the secret's `file:` line and
uncomment its `environment:` line (a secret takes **exactly one** source). Then:

```bash
cp .env.example .env   # fill in the real values
docker compose up --build
```

Compose auto-loads `.env` and feeds the values to the same `/run/secrets/<name>`
paths, so nothing else changes.

### On the host: `make run`

To run outside Docker (uvicorn + Streamlit directly):

```bash
cp .env.example .env   # required — see note below
make run
```

> **Note:** `manage_sensitive` checks `/run/secrets/<name>` → `/workspaces/*/secrets/<name>.txt`
> → environment variable. It does **not** read `/mnt/p/Secrets` directly, so a
> host run always needs the values in `.env` (the Makefile exports them for you).

### Port overrides

Set `LIT_API_PORT` / `LIT_STREAMLIT_PORT` (in `.env` or the environment) to run
alongside other stacks without colliding on 8000/8501.

## Use Case: How to Use the Application

1. **Start the Backend Server:**  
   Run the backend API server using the command:  
   ```bash
   uvicorn app.server:app --host 0.0.0.0 --port 8000 --log-level debug
   ```

2. **Launch the Streamlit UI:**  
   Open the Streamlit app (e.g., `streamlit/ScopingReview_api.py`) to access the interactive web interface.

3. **Enter Research Question:**  
   Input your research question or topic in the provided text area.

4. **Perform Initial Search:**  
   Use the "first search" step to fetch relevant articles. Download the Excel results.

5. **Refine Search with Keywords:**  
   Upload the Excel file and use the keyword suggestion and iterative search steps to refine your article list.

6. **Categorize Articles:**  
   Upload the refined Excel file and define categories to organize articles.

7. **Summarize Categories:**  
   Upload the categorized file to generate summaries in a Word document.

8. **Draft Review:**  
   Upload the summary document to generate a draft review document.

9. **Generate Bibliography:**  
   Upload the finalized article list to generate a BibTeX bibliography file.

This workflow guides users through a comprehensive scoping review process, leveraging AI-assisted search, categorization, summarization, and drafting tools.

## Health Check

The API exposes a health check endpoint at:

```
GET /health
```

which returns a simple JSON response indicating the service status.

## Project Structure Highlights

- `app/server.py`: Main FastAPI app instance and router registrations.
- `app/v01/scoping/`: Contains API routes for scoping review steps.
- `app/v01/standalone/`: Contains standalone API routes for bibliography and summary features.
- `streamlit/`: Contains Streamlit UI and API integration files for the main website.
- `ScopingReview/`: Core logic and workflow management for the scoping review process.