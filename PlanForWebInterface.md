Web Interface Repo
- Home.py (index page)
-- pages
--- 1_emoji_mpog.py
- ScopingReview_submodule
-- streamlit
--- ScopingReview_web.py


.....
1_emoji_mpog.py:

from ScopingReview_submodule.streamlit.ScopingReview_web import show_mpog_page

show_mpog_page()

....
ScopingReview_web.py:

import ScopingReview 
import config 

def show_mpog_page:
    Normal streamlit code


if __name__==_main_:
    show_mpog_page()

....