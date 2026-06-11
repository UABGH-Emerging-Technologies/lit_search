import io

import pandas as pd
from literature_api import (
    categorize_articles,
    draft_article,
    generate_bibtex,
    initial_literature_search,
    initial_literature_search_summary,
    iterate_search,
    summarize_categories,
)

import streamlit as st

try:
    from aiweb_common.streamlit.streamlit_common import (
        apply_uab_font,
        hide_streamlit_branding,
    )
except ImportError:

    def hide_streamlit_branding():
        pass

    def apply_uab_font():
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

WIZARD_STEPS = [
    {
        "num": 1,
        "key": "search",
        "label": "Search",
        "action": "Fetch Articles",
        "icon": ":material/search:",
        "title": "Start with your research question",
        "subtitle": "We'll search PubMed and surface the most relevant articles. You can refine in the next step.",
    },
    {
        "num": 2,
        "key": "iterate",
        "label": "Iterate",
        "action": "Run Iteration",
        "icon": ":material/refresh:",
        "title": "Refine your article selection",
        "subtitle": "Review the search results and iterate to narrow down the most relevant articles.",
    },
    {
        "num": 3,
        "key": "categorize",
        "label": "Categorize",
        "action": "Categorize Articles",
        "icon": ":material/category:",
        "title": "Group articles into themes",
        "subtitle": "Define categories and let AI classify each article into the themes you specify.",
    },
    {
        "num": 4,
        "key": "summarize",
        "label": "Summarize",
        "action": "Summarize Categories",
        "icon": ":material/summarize:",
        "title": "Summarize each category",
        "subtitle": "Generate per-category summaries of your articles for the review narrative.",
    },
    {
        "num": 5,
        "key": "draft",
        "label": "Draft",
        "action": "Draft Article",
        "icon": ":material/edit_note:",
        "title": "Draft your scoping review",
        "subtitle": "Generate a draft narrative from your category summaries.",
    },
    {
        "num": 6,
        "key": "bibtex",
        "label": "Bibliography",
        "action": "Generate Bibliography",
        "icon": ":material/book:",
        "title": "Generate your bibliography",
        "subtitle": "Create a BibTeX file from your finalized article list.",
    },
]

RESULT_KEYS = {
    1: [
        "initial_search_result",
        "initial_search_summary_result",
        "search_finished",
        "scope_df_1",
        "scope_raw_1",
    ],
    2: ["iteration_search_result", "scope_df_2", "scope_raw_2"],
    3: ["categorize_result", "categorization_finished", "scope_df_3", "scope_raw_3"],
    4: ["docx_bytes", "summarize_result", "summarize_warning", "summarization_finished"],
    5: ["draft_result", "draft_complete"],
    6: ["bibtex_result", "bibtex_complete"],
}

STEPPER_CSS = """
<style>
.stepper-wrap {
    display: flex; justify-content: space-between; align-items: flex-start;
    max-width: 720px; margin: 0.5rem auto 1.5rem auto; padding: 0;
}
.stepper-item {
    display: flex; flex-direction: column; align-items: center; flex: 1;
    position: relative; min-width: 0;
}
.stepper-item:not(:last-child)::after {
    content: ''; position: absolute; top: 18px; left: 50%; right: -50%;
    height: 2px; background: #E5E7EB; z-index: 0;
}
.stepper-item.done:not(:last-child)::after { background: #1e6b52; }
.stepper-circle {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 0.95rem; z-index: 1;
    background: #F3F4F6; color: #9CA3AF; border: 2px solid #E5E7EB;
    transition: all 0.2s ease;
}
.stepper-item.done .stepper-circle {
    background: #1e6b52; color: #fff; border-color: #1e6b52;
}
.stepper-item.active .stepper-circle {
    background: #fff; color: #1e6b52; border-color: #1e6b52;
    box-shadow: 0 0 0 4px rgba(30,107,82,0.15);
}
.stepper-label {
    margin-top: 8px; font-size: 0.78rem; color: #9CA3AF;
    text-align: center; white-space: nowrap;
}
.stepper-item.done .stepper-label { color: #1e6b52; font-weight: 500; }
.stepper-item.active .stepper-label { color: #1e6b52; font-weight: 600; }
.step-progress-text {
    text-align: center; font-size: 0.85rem; color: #6B7280;
    margin-bottom: 0.25rem; font-weight: 500;
}
.question-reference {
    background: #F9FAFB; border-radius: 6px; padding: 8px 12px;
    font-size: 13px; display: flex; align-items: center;
    justify-content: space-between;
}
.question-reference-label { color: #9CA3AF; }
.question-reference-text { color: #262730; font-style: italic; margin-left: 4px; }
</style>
"""

EXAMPLE_PROMPTS = [
    "Postop delirium",
    "Sugammadex outcomes",
    "ML for sepsis",
]

LITERATURE_ABOUT = {
    "title": "About This Tool",
    "content": (
        "**How It Works**\n\n"
        "1. **Enter your research question** -- Describe your topic or paste "
        "your specific aims.\n\n"
        "2. **Choose a workflow** -- Run an initial literature search for a quick "
        "overview, or start a full scoping review pipeline.\n\n"
        "3. **Iterate** -- Refine your search, categorize articles, summarize "
        "categories, draft a narrative, or generate a BibTeX file.\n\n"
        "4. **Download** -- Export results at any stage for use in your manuscript."
    ),
    "cases": {
        "quick_search": {
            "title": "Quick Literature Overview",
            "content": (
                "**Scenario:** You have a new research idea and want to see what "
                "has already been published.\n\n"
                "**Steps:**\n"
                "1. Select *Initial literature search*.\n"
                "2. Enter your research question.\n"
                "3. Click **Search** and review the AI-curated results.\n\n"
                "**Result:** A summary of key papers and themes related to your topic, "
                "ready to inform your next steps."
            ),
        },
        "scoping_review": {
            "title": "Full Scoping Review Pipeline",
            "content": (
                "**Scenario:** You are writing a systematic or scoping review and need "
                "a structured workflow.\n\n"
                "**Steps:**\n"
                "1. Select *Work on scoping review*.\n"
                "2. Run the **first search**, then **iterate** to refine.\n"
                "3. **Categorize** articles into themes.\n"
                "4. **Summarize** each category.\n"
                "5. **Draft** a narrative section and **export BibTeX**.\n\n"
                "**Result:** A complete literature review pipeline from search to "
                "draft manuscript text."
            ),
        },
    },
}

LITERATURE_CITATION = (
    "Godwin R, Soundararajan K, Ness T, Bryant A, Melvin R. End-to-End AI "
    "Scoping Review: From Article Retrieval to Complete First Draft. "
    "*Anesthesia & Analgesia.* 2025;140(4S):40."
)

AI_TOOLS_WARNING = """
---

**Responsible Use of AI Tools**

AI-generated content requires human review and may contain errors. You are responsible for verifying all outputs before use.
"""

RESUME_STEPS = {
    "Step 2: Iterate — upload articles with Y/N selections (.xlsx)": {
        "step": 2,
        "types": ["xlsx"],
        "df_target": 1,
        "raw_target": 1,
    },
    "Step 3: Categorize — upload iterated articles (.xlsx)": {
        "step": 3,
        "types": ["xlsx"],
        "df_target": 2,
        "raw_target": 2,
    },
    "Step 4: Summarize — upload categorized articles (.xlsx/.csv)": {
        "step": 4,
        "types": ["xlsx", "csv"],
        "result_key": "categorize_result",
    },
    "Step 5: Draft — upload category summary (.docx)": {
        "step": 5,
        "types": ["docx"],
        "result_key": "docx_bytes",
    },
    "Step 6: Bibliography — upload categorized articles (.xlsx/.docx)": {
        "step": 6,
        "types": ["xlsx", "docx"],
        "result_key": "categorize_result",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


class _FakeUploadedFile:
    def __init__(self, data: bytes, name: str):
        self._data = data
        self.name = name

    def getvalue(self):
        return self._data

    def read(self):
        return self._data

    def seek(self, pos):
        pass


def _df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _xlsx_bytes_to_df(xlsx_bytes: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(xlsx_bytes))


def _init_wizard_state():
    if "scope_current_step" not in st.session_state:
        st.session_state["scope_current_step"] = 1
    if "scope_completed" not in st.session_state:
        st.session_state["scope_completed"] = set()


def _go_to_step(step_num):
    completed = st.session_state.get("scope_completed", set())
    to_clear = {s for s in completed if s >= step_num}
    completed -= to_clear
    st.session_state["scope_completed"] = completed
    st.session_state["scope_current_step"] = step_num
    for s in to_clear:
        for k in RESULT_KEYS.get(s, []):
            st.session_state.pop(k, None)
    st.rerun()


def _mark_complete(step_num):
    completed = st.session_state.get("scope_completed", set())
    completed.add(step_num)
    st.session_state["scope_completed"] = completed


def _reset_wizard():
    for s in range(1, 7):
        for k in RESULT_KEYS.get(s, []):
            st.session_state.pop(k, None)
    st.session_state["scope_completed"] = set()
    st.session_state["scope_current_step"] = 1
    st.session_state["research_q"] = ""
    st.session_state["search_finished"] = False
    st.rerun()


def _get_edited_df(step_num):
    editor_key = f"editor_step{step_num}"
    if editor_key in st.session_state:
        val = st.session_state[editor_key]
        if isinstance(val, dict) and "edited_rows" in val:
            base = st.session_state.get(f"scope_df_{step_num}")
            if base is not None:
                df = base.copy()
                for idx_str, changes in val["edited_rows"].items():
                    for col, new_val in changes.items():
                        df.at[int(idx_str), col] = new_val
                for row in val.get("added_rows", []):
                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                for idx in sorted(val.get("deleted_rows", []), reverse=True):
                    df = df.drop(index=idx).reset_index(drop=True)
                return df
        elif isinstance(val, pd.DataFrame):
            return val
    return st.session_state.get(f"scope_df_{step_num}")


def _save_edited_df(step_num, df: pd.DataFrame):
    st.session_state[f"scope_df_{step_num}"] = df
    editor_key = f"editor_step{step_num}"
    if editor_key in st.session_state:
        del st.session_state[editor_key]


def _get_step_bytes(step_num) -> bytes | None:
    raw = st.session_state.get(f"scope_raw_{step_num}")
    if raw:
        return raw
    df = _get_edited_df(step_num)
    if df is not None:
        return _df_to_xlsx_bytes(df)
    return None


def _snapshot_editor(step_num):
    df = _get_edited_df(step_num)
    if df is not None:
        st.session_state[f"scope_df_{step_num}"] = df
        st.session_state[f"scope_raw_{step_num}"] = _df_to_xlsx_bytes(df)
        editor_key = f"editor_step{step_num}"
        st.session_state.pop(editor_key, None)


def _auto_run_next(step_num):
    st.session_state["scope_auto_run"] = True


def _consume_auto_run() -> bool:
    if st.session_state.pop("scope_auto_run", False):
        return True
    return False


def _extract_research_question(file_bytes: bytes) -> str | None:
    try:
        df2 = pd.read_excel(io.BytesIO(file_bytes), sheet_name="Sheet2")
        if "Input Terms" in df2.columns and len(df2) > 0:
            val = str(df2["Input Terms"].iloc[0]).strip()
            if val and val.lower() != "nan":
                return val
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# UI components
# ─────────────────────────────────────────────────────────────────────────────


def _render_stepper(current, completed):
    st.markdown(STEPPER_CSS, unsafe_allow_html=True)

    progress_text = f"Step {current} of {len(WIZARD_STEPS)} · {WIZARD_STEPS[current-1]['label']}"
    st.markdown(
        f'<div class="step-progress-text">{progress_text}</div>',
        unsafe_allow_html=True,
    )

    html = '<div class="stepper-wrap">'
    for step in WIZARD_STEPS:
        num = step["num"]
        if num in completed and num != current:
            cls, content = "done", "✓"
        elif num == current:
            cls, content = "active", str(num)
        else:
            cls, content = "", str(num)
        html += (
            f'<div class="stepper-item {cls}">'
            f'<div class="stepper-circle">{content}</div>'
            f'<div class="stepper-label">{step["label"]}</div>'
            f"</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _render_question_reference(research_q: str):
    if not research_q.strip():
        return
    col_q, col_reset = st.columns([5, 1], vertical_alignment="center")
    with col_q:
        st.markdown(
            f'<div class="question-reference">'
            f'<span><span class="question-reference-label">Researching:</span>'
            f'<span class="question-reference-text">"{research_q}"</span></span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_reset:
        if st.button(
            "Start over",
            key="reset_wizard_btn",
            use_container_width=True,
            help="Clear all progress and enter a new research question",
        ):
            _reset_wizard()


def _render_step_jump_buttons(current, completed):
    completed_sorted = sorted(s for s in completed if s != current)
    if not completed_sorted:
        return
    with st.expander("Jump back to a completed step", icon=":material/history:"):
        cols = st.columns(len(completed_sorted))
        for i, num in enumerate(completed_sorted):
            with cols[i]:
                step = WIZARD_STEPS[num - 1]
                if st.button(
                    f"Step {num}: {step['label']}",
                    key=f"jump_{num}",
                    use_container_width=True,
                ):
                    _go_to_step(num)


def _render_completion_cta(step_num, dl_data, dl_filename, dl_mime, hint=""):
    if hint:
        st.info(hint, icon=":material/lightbulb:")

    if step_num < 6:
        c1, c2, c3 = st.columns(3)
        next_step = WIZARD_STEPS[step_num]
        with c1:
            if st.button(
                next_step["action"],
                type="primary",
                key=f"continue_{step_num}",
                use_container_width=True,
                icon=next_step.get("icon"),
            ):
                _snapshot_editor(step_num)
                st.session_state["scope_current_step"] = step_num + 1
                _auto_run_next(step_num)
                st.rerun()
        with c2:
            if st.button(
                "Re-run",
                key=f"rerun_{step_num}",
                use_container_width=True,
                icon=":material/refresh:",
            ):
                _go_to_step(step_num)
        with c3:
            st.download_button(
                label="Download",
                data=dl_data,
                file_name=dl_filename,
                mime=dl_mime,
                key=f"dl_{step_num}",
                use_container_width=True,
                icon=":material/download:",
            )
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "Re-run",
                key=f"rerun_{step_num}",
                use_container_width=True,
                icon=":material/refresh:",
            ):
                _go_to_step(step_num)
        with c2:
            st.download_button(
                label="Download",
                data=dl_data,
                file_name=dl_filename,
                mime=dl_mime,
                key=f"dl_{step_num}",
                use_container_width=True,
                icon=":material/download:",
            )


def _render_search_card(value, placeholder, key_prefix):
    with st.container(border=True):
        st.markdown("**Research question or topic**")

        new_value = st.text_area(
            "Research question",
            value=value,
            placeholder=f"{placeholder} — for grants, paste your specific aims",
            height=110,
            label_visibility="collapsed",
            key=f"{key_prefix}_input",
        )

        chips_col, btn_col = st.columns([3, 1], vertical_alignment="bottom")
        with chips_col:
            st.caption("Try one of these:")
            chosen = st.pills(
                "Try",
                EXAMPLE_PROMPTS,
                key=f"{key_prefix}_chips",
                label_visibility="collapsed",
                selection_mode="single",
            )
            if chosen and chosen != st.session_state.get("research_q"):
                st.session_state["research_q"] = chosen
                st.rerun()
        with btn_col:
            clicked = st.button(
                "Fetch Articles",
                type="primary",
                key=f"{key_prefix}_btn",
                use_container_width=True,
                icon=":material/search:",
            )

    st.caption("⚡ Typically 30–60 seconds")

    return new_value, clicked


def _render_resume_session(completed):
    with st.expander("\U0001f4c2 Resume a previous session", expanded=False):
        st.markdown(
            "Pick the step you want to resume from and upload your file from a previous session."
        )

        choice = st.selectbox(
            "Resume from",
            options=list(RESUME_STEPS.keys()),
            label_visibility="collapsed",
            key="resume_choice",
        )
        config = RESUME_STEPS[choice]

        uploaded = st.file_uploader(
            "Upload your file",
            type=config["types"],
            key="resume_upload",
        )

        detected_q = ""
        if uploaded and uploaded.name.endswith(".xlsx"):
            detected_q = _extract_research_question(uploaded.getvalue()) or ""

        resume_q = st.text_input(
            "Research question",
            value=detected_q or st.session_state.get("research_q", ""),
            placeholder="Auto-detected from file, or enter manually",
            key="resume_research_q",
        )

        if detected_q:
            st.caption("✅ Research question auto-detected from your file.")

        if st.button("Resume", type="primary", key="resume_btn", icon=":material/play_arrow:"):
            if not resume_q.strip():
                st.warning("Please enter your research question — it's needed for the API calls.")
                return
            if not uploaded:
                st.warning("Please upload a file first.")
                return

            with st.spinner(
                "Loading your file and resuming session... Please do not leave this page while processing."
            ):
                st.session_state["research_q"] = resume_q

                file_bytes = uploaded.getvalue()
                target_step = config["step"]

                prior = set(range(1, target_step))
                st.session_state["scope_completed"] = prior

                if "raw_target" in config:
                    st.session_state[f"scope_raw_{config['raw_target']}"] = file_bytes
                if "df_target" in config:
                    try:
                        df = _xlsx_bytes_to_df(file_bytes)
                        st.session_state[f"scope_df_{config['df_target']}"] = df
                    except Exception:
                        st.error("Could not read the uploaded file.")
                        return
                if "result_key" in config:
                    st.session_state[config["result_key"]] = file_bytes

                st.session_state["scope_current_step"] = target_step
            st.rerun()


def _render_input_source(prev_step_num, file_label, file_types, key_prefix, prev_data=None):
    if prev_data is not None:
        st.info(
            f"Using results from Step {prev_step_num}: {WIZARD_STEPS[prev_step_num-1]['label']}.",
            icon=":material/auto_awesome:",
        )
        use_own = st.checkbox(
            "Use a different file instead",
            key=f"{key_prefix}_override",
            help="Override the auto-passed results with your own file.",
        )
        if use_own:
            return st.file_uploader(file_label, type=file_types, key=f"{key_prefix}_upload")
        else:
            ext = file_types[0]
            return _FakeUploadedFile(prev_data, f"step_{prev_step_num}_results.{ext}")
    else:
        return st.file_uploader(file_label, type=file_types, key=f"{key_prefix}_upload")


# ─────────────────────────────────────────────────────────────────────────────
# Step renderers
# ─────────────────────────────────────────────────────────────────────────────


def _step_search(_research_q_unused):
    if 1 not in st.session_state.get("scope_completed", set()):
        new_q, fetch_clicked = _render_search_card(
            value=st.session_state.get("research_q", ""),
            placeholder="e.g., variability of lidocaine usage by race in pediatric anesthesia",
            key_prefix="scope",
        )
        st.session_state["research_q"] = new_q

        if fetch_clicked:
            if not new_q.strip():
                st.warning("Please enter a research question first.")
                return
            with st.spinner(
                "Searching PubMed and other sources... Please do not leave this page while processing."
            ):
                finished = initial_literature_search(new_q)
                if finished:
                    st.session_state["search_finished"] = True
                    xlsx = st.session_state.get("initial_search_result")
                    if xlsx:
                        try:
                            _save_edited_df(1, _xlsx_bytes_to_df(xlsx))
                        except Exception:
                            pass
                        st.session_state["scope_raw_1"] = xlsx
                    _mark_complete(1)
                    st.rerun()
                else:
                    st.error("Search failed. Please try again.")
        return

    st.success("Initial search completed.", icon=":material/check_circle:")

    base_df = st.session_state.get("scope_df_1")
    if base_df is not None:
        current_df = _get_edited_df(1)
        st.markdown(
            f"**{len(current_df)} articles found.** Review below and add a Y/N column to mark articles you want to keep."
        )
        st.data_editor(
            base_df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_step1",
        )

        download_df = _get_edited_df(1)
        _render_completion_cta(
            1,
            _df_to_xlsx_bytes(download_df),
            "literature_search_results.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            hint="Mark articles with Y/N, then continue. Your edits are saved automatically.",
        )
    else:
        docx = st.session_state.get("initial_search_summary_result")
        if docx and len(docx) > 0:
            _render_completion_cta(
                1,
                docx,
                "literature_search_summary.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                hint="Download this summary, then continue with your article selections.",
            )
        else:
            st.error("No results available.")


def _run_iterate(uploaded_file, research_q):
    with st.spinner("Iterating search... Please do not leave this page while processing."):
        finished = iterate_search(uploaded_file, research_q)
        if finished:
            xlsx = st.session_state.get("iteration_search_result")
            if xlsx:
                try:
                    _save_edited_df(2, _xlsx_bytes_to_df(xlsx))
                except Exception:
                    pass
                st.session_state["scope_raw_2"] = xlsx
            _mark_complete(2)
            st.rerun()


def _step_iterate(research_q):
    prev_data = _get_step_bytes(1)

    if 2 not in st.session_state.get("scope_completed", set()):
        if _consume_auto_run() and prev_data:
            _run_iterate(_FakeUploadedFile(prev_data, "search_results.xlsx"), research_q)
            return

        st.markdown("Refine your article selection by iterating on the search.")
        uploaded_file = _render_input_source(
            prev_step_num=1,
            file_label="Upload Excel with Y/N selections",
            file_types=["xlsx"],
            key_prefix="scope_iter",
            prev_data=prev_data,
        )

        if st.button(
            "Run Iteration", icon=":material/refresh:", type="primary", key="scope_iter_run"
        ):
            if not uploaded_file:
                st.warning("Please provide a file first.")
                return
            _run_iterate(uploaded_file, research_q)
        return

    st.success("Iteration completed.", icon=":material/check_circle:")
    base_df = st.session_state.get("scope_df_2")
    if base_df is not None:
        current_df = _get_edited_df(2)
        st.markdown(f"**{len(current_df)} refined articles.** Review and edit as needed.")
        st.data_editor(
            base_df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_step2",
        )
        download_df = _get_edited_df(2)
        _render_completion_cta(
            2,
            _df_to_xlsx_bytes(download_df),
            "iteration_search_results.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            hint="Continue to categorize the refined articles into themes.",
        )


def _step_categorize(research_q):
    prev_data = _get_step_bytes(2)

    if 3 not in st.session_state.get("scope_completed", set()):
        st.markdown("Group your refined articles into themes you define.")
        uploaded_file = _render_input_source(
            prev_step_num=2,
            file_label="Upload Excel file to categorize",
            file_types=["xlsx"],
            key_prefix="scope_cat",
            prev_data=prev_data,
        )

        userdefined_categories = st.text_area(
            "Categories (comma-separated)",
            placeholder="e.g., Clinical Trials, Observational Studies, Reviews",
            key="scope_cat_input",
            height=80,
        )

        if st.button(
            "Run Categorization", icon=":material/category:", type="primary", key="scope_cat_run"
        ):
            if not uploaded_file:
                st.warning("Please provide a file first.")
                return
            if not userdefined_categories.strip():
                st.warning("Please enter at least one category.")
                return
            with st.spinner(
                "Categorizing articles... Please do not leave this page while processing."
            ):
                finished = categorize_articles(uploaded_file, userdefined_categories, research_q)
                if finished:
                    xlsx = st.session_state.get("categorize_result")
                    if xlsx:
                        try:
                            _save_edited_df(3, _xlsx_bytes_to_df(xlsx))
                        except Exception:
                            pass
                        st.session_state["scope_raw_3"] = xlsx
                    _mark_complete(3)
                    st.rerun()
        return

    st.success("Categorization completed.", icon=":material/check_circle:")
    base_df = st.session_state.get("scope_df_3")
    if base_df is not None:
        current_df = _get_edited_df(3)
        st.markdown(f"**{len(current_df)} articles categorized.** Review the assignments below.")
        st.data_editor(
            base_df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_step3",
        )

        download_df = _get_edited_df(3)
        xlsx_bytes = _df_to_xlsx_bytes(download_df)
        st.session_state["categorize_result"] = xlsx_bytes
        _render_completion_cta(
            3,
            xlsx_bytes,
            "categorized_articles.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            hint="These results will feed into Step 4 (Summarize) and Step 6 (Bibliography).",
        )


def _run_summarize(uploaded_file, research_q):
    with st.spinner(
        "Summarizing articles by category... Please do not leave this page while processing."
    ):
        finished = summarize_categories(uploaded_file, research_q)
        if finished:
            _mark_complete(4)
            st.rerun()


def _step_summarize(research_q):
    cat_result = st.session_state.get("categorize_result")

    if 4 not in st.session_state.get("scope_completed", set()):
        if _consume_auto_run() and cat_result:
            _run_summarize(_FakeUploadedFile(cat_result, "categorized_articles.xlsx"), research_q)
            return

        st.markdown("Generate per-category summaries of your articles.")
        uploaded_file = _render_input_source(
            prev_step_num=3,
            file_label="Upload Excel or CSV file",
            file_types=["xlsx", "csv"],
            key_prefix="scope_sum",
            prev_data=cat_result,
        )

        if st.button(
            "Summarize Categories", icon=":material/summarize:", type="primary", key="scope_sum_run"
        ):
            if not uploaded_file:
                st.warning("Please provide a file first.")
                return
            _run_summarize(uploaded_file, research_q)
        return

    docx = st.session_state.get("docx_bytes")
    if docx:
        warn = st.session_state.get("summarize_warning")
        if warn:
            st.warning(warn)
        st.success("Summarization completed.", icon=":material/check_circle:")
        _render_completion_cta(
            4,
            docx,
            "summary_categories.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            hint="This summary will be used in Step 5 to draft the article.",
        )


def _run_draft(uploaded_file, research_q):
    with st.spinner("Drafting article... Please do not leave this page while processing."):
        draft_bytes = draft_article(uploaded_file, research_q)
        if draft_bytes is not None:
            st.session_state["draft_result"] = draft_bytes
            _mark_complete(5)
            st.rerun()
        else:
            st.error("Drafting failed.")


def _step_draft(research_q):
    sum_result = st.session_state.get("docx_bytes")

    if 5 not in st.session_state.get("scope_completed", set()):
        if _consume_auto_run() and sum_result:
            _run_draft(_FakeUploadedFile(sum_result, "summary_categories.docx"), research_q)
            return

        st.markdown("Generate a draft scoping review article from your category summaries.")
        uploaded_file = _render_input_source(
            prev_step_num=4,
            file_label="Upload summary document (.docx)",
            file_types=["docx"],
            key_prefix="scope_draft",
            prev_data=sum_result,
        )

        if st.button(
            "Draft Article", icon=":material/edit_note:", type="primary", key="scope_draft_run"
        ):
            if not uploaded_file:
                st.warning("Please provide a file first.")
                return
            _run_draft(uploaded_file, research_q)
        return

    docx = st.session_state.get("draft_result")
    if docx:
        st.success("Draft completed.", icon=":material/check_circle:")
        _render_completion_cta(
            5,
            docx,
            "draft_review.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


def _run_bibtex(uploaded_file):
    with st.spinner("Generating bibliography... Please do not leave this page while processing."):
        finished = generate_bibtex(uploaded_file)
        if finished:
            _mark_complete(6)
            st.rerun()


def _step_bibtex(research_q):
    cat_result = st.session_state.get("categorize_result")

    if 6 not in st.session_state.get("scope_completed", set()):
        if _consume_auto_run() and cat_result:
            _run_bibtex(_FakeUploadedFile(cat_result, "categorized_articles.xlsx"))
            return

        st.markdown("Generate a BibTeX bibliography file from your finalized article list.")
        uploaded_file = _render_input_source(
            prev_step_num=3,
            file_label="Upload Excel or DOCX file",
            file_types=["xlsx", "docx"],
            key_prefix="scope_bib",
            prev_data=cat_result,
        )

        if st.button(
            "Generate Bibliography", icon=":material/book:", type="primary", key="scope_bib_run"
        ):
            if not uploaded_file:
                st.warning("Please provide a file first.")
                return
            _run_bibtex(uploaded_file)
        return

    bib = st.session_state.get("bibtex_result")
    if bib:
        st.success("Bibliography generated.", icon=":material/check_circle:")
        _render_completion_cta(
            6,
            bib,
            "bibliography.bib",
            "application/x-bibtex",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main page
# ─────────────────────────────────────────────────────────────────────────────


def show_literature_search_page():
    st.set_page_config(page_title="Literature Search", page_icon="\U0001f4da", layout="wide")
    hide_streamlit_branding()
    apply_uab_font()

    st.markdown(
        """
    <style>
    button[data-testid="stBaseButton-segmented_controlActive"] {
        background-color: #144b39 !important;
        color: #fff !important;
        border-color: #144b39 !important;
    }
    button[data-testid="stBaseButton-segmented_controlActive"] p {
        color: #fff !important;
    }
    .st-key-mode_toggle {
        display: flex !important;
        justify-content: center !important;
    }
    div.stButton {
        display: flex;
        justify-content: center;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<h1 style="text-align: center;">\U0001f4da Literature Search</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align: center; color: #6B7280; margin-top: -0.5rem;">'
        "Use generative AI to situate your research question in the context of existing literature."
        "</p>",
        unsafe_allow_html=True,
    )

    with st.expander(LITERATURE_ABOUT["title"]):
        st.markdown(LITERATURE_ABOUT["content"])
        for case_key, case_data in LITERATURE_ABOUT["cases"].items():
            with st.expander(case_data["title"]):
                st.markdown(case_data["content"])

    mode = st.segmented_control(
        "Search mode",
        options=["Initial literature search", "Work on scoping review"],
        default="Initial literature search",
        label_visibility="collapsed",
        key="mode_toggle",
    )

    prev_mode = st.session_state.get("prev_query_type")
    if prev_mode != mode:
        st.session_state["search_finished"] = False
        st.session_state["prev_query_type"] = mode

    if "research_q" not in st.session_state:
        st.session_state["research_q"] = ""

    # ── Initial literature search mode ──
    if mode == "Initial literature search":
        new_q, fetch_clicked = _render_search_card(
            value=st.session_state["research_q"],
            placeholder="e.g., variability of lidocaine usage by race",
            key_prefix="initial",
        )

        if new_q != st.session_state["research_q"]:
            st.session_state["research_q"] = new_q
            st.session_state["search_finished"] = False

        research_q = st.session_state["research_q"]

        if fetch_clicked:
            if not research_q.strip():
                st.warning("Please enter a research question first.")
            else:
                with st.spinner("Searching... Please do not leave this page while processing."):
                    finished = initial_literature_search_summary(research_q)
                    if finished:
                        st.session_state["search_finished"] = True
                    else:
                        st.error("Failed to generate search results.")

        if st.session_state.get("search_finished", False):
            docx_bytes = st.session_state.get("initial_search_summary_result")
            excel_bytes = st.session_state.get("initial_search_result")

            if docx_bytes and len(docx_bytes) > 0:
                st.success("Search completed successfully.", icon=":material/check_circle:")
                st.download_button(
                    label="Download Summary (.docx)",
                    icon=":material/description:",
                    data=docx_bytes,
                    file_name="Literature_Survey.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            elif excel_bytes and len(excel_bytes) > 0:
                st.success("Search completed successfully.", icon=":material/check_circle:")
                st.download_button(
                    label="Download Results (.xlsx)",
                    icon=":material/table_chart:",
                    data=excel_bytes,
                    file_name="literature_search_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.error("No search results available for download.")

    # ── Scoping review wizard mode ──
    elif mode == "Work on scoping review":
        _init_wizard_state()
        current = st.session_state["scope_current_step"]
        completed = st.session_state["scope_completed"]
        past_step_1 = current > 1 or 1 in completed

        _render_stepper(current, completed)

        if past_step_1:
            research_q = st.session_state.get("research_q", "")
            _render_question_reference(research_q)

        _render_step_jump_buttons(current, completed)
        _render_resume_session(completed)

        if current == 1 and not completed:
            st.info(
                "**How this works:** Each step builds on the previous one. "
                "Results pass automatically between steps — you can re-run any step or download results at any point.",
                icon=":material/info:",
            )

        step_info = WIZARD_STEPS[current - 1]
        st.markdown(
            f'<p style="font-size: 12px; font-weight: 500; letter-spacing: 0.08em; '
            f'text-transform: uppercase; color: #1e6b52; margin-bottom: 4px;">'
            f"STEP {current} OF {len(WIZARD_STEPS)}</p>"
            f'<h3 style="margin-top: 0; margin-bottom: 4px; color: #1f2933;">{step_info["title"]}</h3>'
            f'<p style="font-size: 14px; color: #5a6470; line-height: 1.5; margin-bottom: 1rem;">'
            f'{step_info["subtitle"]}</p>',
            unsafe_allow_html=True,
        )

        research_q = st.session_state.get("research_q", "")
        if (
            "prev_research_q" not in st.session_state
            or st.session_state["prev_research_q"] != research_q
        ):
            st.session_state["search_finished"] = False
            st.session_state["prev_research_q"] = research_q

        step_renderers = {
            1: _step_search,
            2: _step_iterate,
            3: _step_categorize,
            4: _step_summarize,
            5: _step_draft,
            6: _step_bibtex,
        }
        step_renderers[current](research_q)

    st.caption(LITERATURE_CITATION)
    st.markdown(AI_TOOLS_WARNING, unsafe_allow_html=True)


if __name__ == "__main__":
    show_literature_search_page()
