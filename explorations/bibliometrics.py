import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from pybliometrics.scopus import ScopusSearch, CitationOverview, init
import time

# Initialize pybliometrics (ensure that your API key is configured)
init()

def get_aggregated_citations(query, start_year, end_year):
    """
    Perform a ScopusSearch with the given query.
    For each article, retrieve its citation timeline (from start_year up to end_year)
    and aggregate the yearly citation counts.
    
    Also, if available, count the number of articles published within the 
    N‑year period (based on the 'coverDate' field) to compute an N‑year impact factor.
    
    Returns:
        years: list of years (from start_year to end_year)
        aggregate: numpy array with aggregated yearly citations
        cumulative: numpy array with cumulative citations over the N-year period
        article_count: total number of articles returned by the search
        pub_count: number of articles published within [start_year, end_year]
    """
    # Run the Scopus search
    s = ScopusSearch(query)
    df = pd.DataFrame(s.results)
    article_count = len(df)
    if article_count == 0:
        return None, None, None, 0, 0

    # Attempt to extract publication years from the 'coverDate' field (if available)
    if 'coverDate' in df.columns:
        df['pub_year'] = pd.to_datetime(df['coverDate'], errors='coerce').dt.year
        pub_count = df[(df['pub_year'] >= start_year) & (df['pub_year'] <= end_year)].shape[0]
    else:
        pub_count = article_count

    num_years = end_year - start_year + 1
    years = list(range(start_year, end_year + 1))
    aggregate = np.zeros(num_years, dtype=int)
    cit_article_count = 0

    # Create a progress bar and a placeholder for status messages.
    progress_bar = st.progress(0, text="Starting citation data retrieval...")
    status_text = st.empty()

    for i, (_, row) in enumerate(df.iterrows()):
        status_text.text(f"Processing article {i+1}/{article_count} (scopus_id: {row.get('scopus_id')})")
        scopus_id = row.get('scopus_id')
        if not scopus_id:
            continue  # skip if there is no scopus_id

        # Attempt to fetch the citation timeline for this article
        try:
            # CitationOverview returns an object with an attribute columnTotal that is a list 
            # of citation counts for successive years, starting at start_year.
            citation_overview = CitationOverview([scopus_id], start=start_year, id_type='scopus_id')
            timeline = np.array(citation_overview.columnTotal)
            # Pad with zeros if timeline is shorter; truncate if longer than requested
            if timeline.size < num_years:
                timeline = np.concatenate([timeline, np.zeros(num_years - timeline.size, dtype=int)])
            elif timeline.size > num_years:
                timeline = timeline[:num_years]

            aggregate += timeline
            cit_article_count += 1

        except Exception as e:
            st.warning(f"Could not fetch citation details for scopus_id {scopus_id}: {e}")

        # Update the progress bar after processing each article
        progress_bar.progress((i + 1) / article_count, text="Fetching citation data...")
        time.sleep(0.1)  # Slight delay to be gentle on the API

    status_text.text("Finished processing articles.")
    progress_bar.empty()  # Remove the progress bar
    cumulative = np.cumsum(aggregate)
    return years, aggregate, cumulative, article_count, pub_count

def main():
    st.title("Citation Timeline Visualizer using pybliometrics")
    st.write(
        "Enter a Scopus query along with a start and end year. "
        "For each retrieved article, the citation timeline between "
        "those years is fetched and aggregated to display a yearly and cumulative chart. "
        "Additionally, an N‑year impact factor is computed as total citations divided by "
        "the number of publications within the chosen period."
    )

    with st.form(key='query_form'):
        query = st.text_input(
            "Scopus Query",
            value="( SRCTITLE ( Physiological Reviews) ) AND ( PUBYEAR < 2018 ) AND ( PUBYEAR > 2014 )"
        )
        start_year = st.number_input("Start Year", min_value=1900, max_value=2100, value=2015, step=1)
        end_year = st.number_input("End Year", min_value=1900, max_value=2100, value=2018, step=1)
        submit_button = st.form_submit_button(label="Visualize")

    if submit_button:
        if start_year > end_year:
            st.error("Error: Start Year must be less than or equal to End Year.")
            return

        with st.spinner("Searching Scopus and retrieving citation data..."):
            result = get_aggregated_citations(query, start_year, end_year)
        if result[0] is None:
            st.error("No articles found for the given query.")
            return

        years, yearly_citations, cumulative_citations, total_articles, pub_count = result
        total_citations = cumulative_citations[-1]
        # Compute the N-year (impact factor) as total citations in the period divided by publications
        n_year_impact_factor = round(total_citations / pub_count, 2) if pub_count > 0 else 0

        st.subheader(f'Results for query: "{query}"')
        st.write(f"Total articles found by search: **{total_articles}**")
        st.write(f"Publications within {start_year}-{end_year}: **{pub_count}**")
        st.write(f"Total aggregated citations (for {start_year}-{end_year}): **{total_citations}**")
        st.write(f"N‑Year Impact Factor: **{n_year_impact_factor}**")

        # Prepare a pandas DataFrame for charting with Altair
        data = pd.DataFrame({
            "Year": years,
            "Yearly Citations": yearly_citations,
            "Cumulative Citations": cumulative_citations
        })

        # Create an Altair chart with two layered line plots and independent y-axes
        base = alt.Chart(data).encode(x=alt.X("Year:O", title="Year"))
        line_yearly = base.mark_line(color='blue').encode(
            y=alt.Y("Yearly Citations:Q", title="Yearly Citations")
        )
        line_cumulative = base.mark_line(color='green').encode(
            y=alt.Y("Cumulative Citations:Q", title="Cumulative Citations")
        )
        chart = alt.layer(
            line_yearly,
            line_cumulative
        ).resolve_scale(
            y='independent'
        ).properties(
            title="Yearly and Cumulative Citation Timeline",
            width=700,
            height=400
        )

        st.altair_chart(chart, use_container_width=True)

if __name__ == "__main__":
    main()