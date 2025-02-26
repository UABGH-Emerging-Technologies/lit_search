import gradio as gr
from ScopingReview.search import SearchManager

def initial_search(research_query):
    # Function to simulate initial literature search.
    search_manager = SearchManager(scoping_step="first search", research_q=research_query)
    # Simulate a search; replace with actual search logic integration
    results = f"Found results for query: {research_query}"
    return results

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
