import streamlit as st

class StateMachine():
    def __init__(self):
        pass
    
    def initialize_states(self):
        if 'button_clicked' not in st.session_state:
            st.session_state['button_clicked'] = False
            
    def cleanup_states(self):
        for key in st.session_state.keys():
            del st.session_state[key]                
            
## Step 1 - initial search
class StateMachineSearch(StateMachine):
    def __init__(self):
        pass 
    
    def initialize_states(self):
        super().initialize_states()
        if 'search_finished' not in st.session_state:
            st.session_state['search_finished'] = False
            

## Step 2 - iterate on initial search and refine with keywords
class StateMachineIterate(StateMachine): 
    def __init__(self):
        pass
    
    def initialize_states(self):
        super().initialize_states() 
        if 'keywords_extracted' not in st.session_state:
            st.session_state['keywords_extracted'] = False
        if 'keywords_finalized' not in st.session_state:
            st.session_state['keywords_finalized'] = False    
        if 'search_finished' not in st.session_state:
            st.session_state['search_finished'] = False
            
    def cleanup_states(self):
        del st.session_state['search_finished']
        del st.session_state['button_clicked']
        del st.session_state['search_manager']
        st.session_state["keywords_finalized"] = False    

## Step 3 - categorize search results into user defined categories
class StateMachineCategorize(StateMachine):
    def __init__(self):
        pass
    
    def initialize_states(self):
        super().initialize_states() 
        if 'categorization_finished' not in st.session_state:
            st.session_state['categorization_finished'] = False     
            
## Step 4 - create summaries of each subcategory    
class StateMachineSummarize(StateMachine):
    def __init__(self):
        pass
    def initialize_states(self):
        super().initialize_states() 
        if 'summarization_finished' not in st.session_state:
            st.session_state['summarization_finished'] = False     
        if 'subcategorize_complete' not in st.session_state:
            st.session_state['subcategorize_complete'] = False
        if 'summarization_manager' not in st.session_state:
            st.session_state['summarization_manager'] = None

## Step 5 - Summarize Summaries and compile draft
class StateMachineDraft(StateMachine):
    def __init__(self):
        pass
    def initialize_states(self):
        super().initialize_states() 
        if 'draft_complete' not in st.session_state:
            st.session_state['draft_complete'] = False
        if 'draft_manager' not in st.session_state:
            st.session_state['draft_manager'] = None            
            