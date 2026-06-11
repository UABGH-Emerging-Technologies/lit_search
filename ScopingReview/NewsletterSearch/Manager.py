from ScopingReview.InitialSearch.Manager import BaseSearchManager


class NewsletterSearchManager(BaseSearchManager):
    """Executes a predefined PubMed query for newsletter article retrieval.

    Args:
        scoping_step: Identifier for the current scoping step.
        predefined_query: Pre-built PubMed query string.
        research_q: The research question for context.
    """

    def __init__(self, scoping_step, predefined_query, research_q):
        super().__init__(scoping_step, research_q)
        self.predefined_query = predefined_query

    def make_query(self):
        """Return the predefined PubMed query string."""
        return self.predefined_query

    def perform_search(self, search_string):
        """Execute a PubMed search and return the article DataFrame.

        Args:
            search_string: PubMed query string.

        Returns:
            DataFrame of article metadata.
        """
        articles_df = self._fetch_articles(search_string)
        return articles_df
