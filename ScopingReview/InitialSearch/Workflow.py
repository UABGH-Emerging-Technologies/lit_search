import os
from Bio import Entrez
from aiweb_common.resource.PubMedQuery import PubMedQueryGenerator
from aiweb_common.WorkflowHandler import WorkflowHandler
from ScopingReview.InitialSearch.Manager import FastAPISearchManager
from ScopingReview_config import app_config, config

# Ensure Entrez is configured
Entrez.email = config.DEV_EMAIL
os.environ["NCBI_API_KEY"] = app_config.NCBI_API_KEY


class CustomPubMedQueryGenerator(PubMedQueryGenerator):
    """
    Concrete subclass of the package's PubMedQueryGenerator.
    Implements the missing `process` method by delegating to generate_search_string().
    """

    def process(self, loop_n: int = 0, last_query: str = "") -> str:
        """
        Return the LLM‐generated PubMed search string.
        """
        return self.generate_search_string(loop_n=loop_n, last_query=last_query)


class ArticleSearch(WorkflowHandler):
    """
    Performs an iterative PubMed search:
      1. Use LLM to build a query string.
      2. Search PubMed for article IDs.
      3. Fetch details when enough IDs are found.
      4. Retry up to MAX_TRIES if too few.
    """

    def __init__(self, research_question: str):
        super().__init__()
        self.research_question = research_question
        self.search_manager = FastAPISearchManager(
            scoping_step=None, research_q=research_question
        )

    def process(self):
        """
        Loop until we get more than MIN_ARTICLES or exhaust MAX_TRIES.
        Returns a pandas.DataFrame of article details, or None on failure.
        """
        # Use our concrete wrapper instead of the abstract base class
        query_generator = CustomPubMedQueryGenerator(
            config.LLM_INTERFACE, self.research_question
        )

        n = 0
        search_string = ""
        print("Generating PubMed Queries")

        while n <= config.MAX_TRIES:
            # This calls our `process()`, which in turn calls generate_search_string()
            search_string = query_generator.process(loop_n=n, last_query=search_string)
            print("QUERY ‑", search_string)

            article_ids = (
                self.search_manager.pubmed_interface
                .search_pubmed_articles(search_string)
            )
            print("Number of articles found ‑", len(article_ids))

            if len(article_ids) > config.MIN_ARTICLES:
                # Enough articles: fetch details and return
                return (
                    self.search_manager.pubmed_interface
                    .fetch_article_details(article_ids)
                )

            n += 1

        print(f"Insufficient number of articles found in {config.MAX_TRIES} tries")
        return None