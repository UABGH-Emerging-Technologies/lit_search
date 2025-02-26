import gradio as gr
from ScopingReview.search import SearchManager

def initial_search(research_query):
    # Function to perform the initial literature search using SearchManager.
    search_manager = SearchManager(scoping_step="first search", research_q=research_query)
    search_manager.make_query()
    results = search_manager.search_and_compile_articles(write_excel=False)
    return f"Initial search executed. Results: {results}"

def scoping_review_interface(query_input):
    if query_input.strip() == "":
        return "Please provide a query."
    return initial_search(query_input)

def main():
    iface = gr.Interface(
        fn=scoping_review_interface,
        inputs=gr.components.Textbox(label="Enter Research Query"),
        outputs=gr.components.Textbox(label="Result"),
        title="Gradio Scoping Review Interface",
        description="Submit your query to perform an initial literature search for the scoping review."
    )
    iface.launch(server_name="0.0.0.0", share=False)

if __name__ == "__main__":
    main()
