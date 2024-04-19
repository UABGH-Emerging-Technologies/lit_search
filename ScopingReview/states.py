import streamlit as st


class StateMachine:
    def __init__(self):
        pass

    def initialize_states(self):
        if "button_clicked" not in st.session_state:
            st.session_state["button_clicked"] = False

    def cleanup_states(self):
        for key in st.session_state.keys():
            del st.session_state[key]


## Step 1 - initial search
class SearchHandler(StateMachine):
    def __init__(self):
        pass

    def initialize_states(self):
        super().initialize_states()
        if "search_finished" not in st.session_state:
            st.session_state["search_finished"] = False


## Step 2 - iterate on initial search and refine with keywords
class IterateHandler(StateMachine):
    def __init__(self):
        pass

    def initialize_states(self):
        super().initialize_states()
        if "search_manager" not in st.session_state:
            st.session_state["search_manager"] = None
        if "keywords_extracted" not in st.session_state:
            st.session_state["keywords_extracted"] = False
        if "keywords_finalized" not in st.session_state:
            st.session_state["keywords_finalized"] = False
        if "search_finished" not in st.session_state:
            st.session_state["search_finished"] = False

    def cleanup_states(self):
        del st.session_state["search_finished"]
        del st.session_state["button_clicked"]
        del st.session_state["search_manager"]
        st.session_state["keywords_finalized"] = False


## Step 3 - categorize search results into user defined categories
class CategorizeHandler(StateMachine):
    def __init__(self):
        pass

    def initialize_states(self):
        super().initialize_states()
        if "categorization_finished" not in st.session_state:
            st.session_state["categorization_finished"] = False
        if "categorization_manager" not in st.session_state:
            st.session_state["categorization_manager"] = None


## Step 4 - create summaries of each subcategory
class SummarizeHandler(StateMachine):
    def __init__(self):
        pass

    def initialize_states(self):
        super().initialize_states()
        if "summarization_finished" not in st.session_state:
            st.session_state["summarization_finished"] = False
        if "subcategorize_complete" not in st.session_state:
            st.session_state["subcategorize_complete"] = False
        if "summarization_manager" not in st.session_state:
            st.session_state["summarization_manager"] = None
        if "limit_exceeded" not in st.session_state:
            st.session_state["limit_exceeded"] = False
        if "button_clicked" not in st.session_state:
            st.session_state["button_clicked"] = False

    def cleanup_states(self):
        del st.session_state["summarization_manager"]
        del st.session_state["button_clicked"]
        del st.session_state["summarization_finished"]
        del st.session_state["limit_exceeded"]


## Step 5 - Summarize Summaries and compile draft
class DraftHandler(StateMachine):
    def __init__(self):
        pass

    def initialize_states(self):
        super().initialize_states()
        if "draft_complete" not in st.session_state:
            st.session_state["draft_complete"] = False
        if "draft_manager" not in st.session_state:
            st.session_state["draft_manager"] = None


## Step 6 - Generate Bibtex
class BibtexHandler(StateMachine):
    def initialize_states(self):
        super().initialize_states()
        if "bibtex_complete" not in st.session_state:
            st.session_state["bibtex_complete"] = False
        if "bibtex_manager" not in st.session_state:
            st.session_state["bibtex_manager"] = None
