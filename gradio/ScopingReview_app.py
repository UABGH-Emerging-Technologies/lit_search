import gradio as gr
from ScopingReview.search import SearchManager

def initial_search(research_query):
    # Function to perform the initial literature search using SearchManager.
    search_manager = SearchManager(scoping_step="first search", research_q=research_query)
    search_manager.make_query()
    results = search_manager.search_and_compile_articles(write_excel=False)
    return f"Initial search executed. Results: {results}"

def scoping_review_interface(query_type, research_query, scoping_step):
    if research_query.strip() == "":
        return "Please provide a research query."
    if query_type == "work on scoping review":
        # Simulate the behavior of:
        #   self.scoping_step = st.radio("What step of the scoping review do you want to work on?", self.scoping_steps)
        #   self._manage_scoping_review(self.template_location)
        return f"Working on scoping review with step '{scoping_step}' for query '{research_query}'"
    else:
        return initial_search(research_query)

def main():
    iface = gr.Interface(
        fn=scoping_review_interface,
        inputs=[
            gr.components.Radio(choices=["initial literature search", "work on scoping review"], label="Query Type"),
            gr.components.Textbox(label="Enter Research Query"),
            gr.components.Radio(choices=["first search", "iterate on search", "categorize articles", "summarize categories", "draft article", "manage bibtex"], label="Scoping Step")
        ],
        outputs=gr.components.Textbox(label="Result"),
        title="Gradio Scoping Review Interface",
        description="Submit your query to perform a scoping review operation."
    )
    iface.launch(server_name="0.0.0.0", share=False)

if __name__ == "__main__":
    main()
