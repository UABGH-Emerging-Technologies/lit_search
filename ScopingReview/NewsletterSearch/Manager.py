from ScopingReview.InitialSearch.Manager import BaseSearchManager


# The `NewsletterSearchManager` class is a subclass of `BaseSearchManager` that allows for performing
# searches using a predefined query.
class NewsletterSearchManager(BaseSearchManager):
    def __init__(self, scoping_step, predefined_query, research_q):
        super().__init__(scoping_step, research_q)
        self.predefined_query = predefined_query

    def make_query(self):
        return self.predefined_query

    def perform_search(self, search_string):
        articles_df = self._fetch_articles(search_string)
        return articles_df


