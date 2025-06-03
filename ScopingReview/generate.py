from langchain.schema import HumanMessage, SystemMessage
from langchain_community.callbacks import get_openai_callback
from langchain_text_splitters import RecursiveCharacterTextSplitter

import ScopingReview.data as review_data
import ScopingReview.prompts as lit_prompts
import ScopingReview_config.boilerplate as lit_boilerplate
import ScopingReview_config.config as lit_config


def categorize(category_df, input_text):
    # TODO: change the category_df to reduced_df --- in all places
    reduced_df = review_data.get_relevant_rows(category_df)
    cost = 0.0
    input_list = input_text.split(",")
    input_list = [value.strip() for value in input_list if value.strip()]

    for index, row in reduced_df.iterrows():
        data = row[["abstract", "title"]]
        with get_openai_callback() as response_meta:
            result = lit_config.CHAT35.invoke(
                lit_prompts.categorization_chat_prompt.format_prompt(
                    categories=input_list, context=data
                ).to_messages()
            )
        keyword_list = result.content.replace("'", "")
        reduced_df.at[index, "category"] = keyword_list.lower()
    return reduced_df, response_meta


def categories_limit_check(df):
    categories_exceeding_limit = []
    if df is not None:
        df["category"] = df["category"].str.split(", ")
        df_exploded = df.explode("category")

        unique_values_counts = df_exploded["category"].value_counts()
        # print(unique_values_counts)
        for category, count in unique_values_counts.items():
            if count > lit_config.SUBCLASS_THRESHOLD:
                categories_exceeding_limit.append(category)

    return categories_exceeding_limit


def sub_categorize(original_df, categories_exceeding_limit, sub_categories):
    df_copy = original_df.copy()
    reduced_df = review_data.get_relevant_rows(df_copy)
    # should already be transformed to a python list by categories_limit_check()
    df_exploded = reduced_df.explode("category")

    # Prepare new sub-categories
    sub_categories = [value.strip() for value in sub_categories.split(",") if value.strip()]
    # Replace categories exceeding limit with sub-categories
    for remove_category in categories_exceeding_limit:
        remove_category = remove_category.strip()
        remove_category = remove_category.lower()
        df_exploded["category"] = df_exploded["category"].str.lower()
        mask = df_exploded["category"] == remove_category
        for index, row in df_exploded[mask].iterrows():
            # index is preserved across the explode
            if row.category == remove_category:
                data = row[["abstract", "title"]]
                # Assuming your categorization process is correctly set up
                with get_openai_callback() as response_meta:
                    result = lit_config.CHAT35.invoke(
                        lit_prompts.categorization_chat_prompt.format_prompt(
                            categories=sub_categories, context=data
                        ).to_messages()
                    )
                category_to_write = result.content.replace("'", "")
                df_exploded.at[index, "category"] = category_to_write.lower()

    df_final, unique_values_list = recombine_categories(df_exploded, df_copy)

    return df_final, "".join(map(str, unique_values_list)), response_meta


def recombine_categories(df, df_original):
    # Convert all unique categories to string before forming the list
    unique_values_list = list(df["category"].astype(str).unique())
    # Convert the 'category' column to string
    df["category"] = df["category"].astype(str)
    # remove duplicates, possibly created by multiple categories being subcategorized
    df.drop_duplicates(subset=["PMID", "category"], keep="first", inplace=True)
    # Reverse the explode operation to update original dataframe
    df = df.groupby(df.index).agg({"category": lambda x: ", ".join(x), "Relevant": "first"})

    # Merging other columns back into the df
    df_final = df_original.drop(columns=["category", "Relevant"]).merge(
        df, left_index=True, right_index=True, how="right"
    )

    return df_final, unique_values_list


def summarize_article_in_chunks(article_text):
    # Splitting the article text into manageable chunks
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=13000, chunk_overlap=1000
    )
    texts = text_splitter.create_documents([article_text])
    # Create the initial summary for the first chunk
    summary = lit_config.CHAT35.invoke(lit_prompts.initial_summary_prompt.format(text=texts[0]))

    # Iteratively refine the summary with each subsequent chunk
    if len(texts) > 1:
        for text_chunk in texts[1:]:
            summary = lit_config.CHAT35.invoke(
                lit_prompts.refine_summary_prompt.format(existing_summary=summary, text=text_chunk)
            )

    return summary


def summarize_all_categories(df, user_question, newsletter_flag=False):
    # use abtract when text is not available.
    df["Text"] = df.apply(
        lambda row: row["abstract"] if row["Text"] == "Text not available" else row["Text"], axis=1
    )

    # if no abstract or text, remove the article
    df.dropna(inplace=True, subset=["Text"])
    # takes in multiple categories and assigns them in each row
    # TODO change the coln name from Catoegory to Categories
    df_exploded = df.explode("category")

    # get categories
    categories = df_exploded["category"].unique()

    output = []
    for current_category in categories:
        with get_openai_callback() as response_meta:
            filtered_rows = df_exploded[df_exploded["category"] == current_category]
            article_summaries = []
            for idx, row in filtered_rows.iterrows():
                article_summary = summarize_article_in_chunks(row.Text)
                # TODO: nice to haves
                # df_exploded.at[idx, 'Article Summary'] = article_summary
                formatted_summary = (
                    f"APA Citation: {row.citation}\n\n Summary: {article_summary}\n\n --- "
                )
                article_summaries.append(formatted_summary)
            text_to_summarize = "\n\n".join(article_summaries)

            if newsletter_flag:
                result = lit_config.CHAT.invoke(
                    lit_prompts.newsletter_chat_prompt.format_prompt(
                        category=current_category, content=text_to_summarize
                    ).to_messages()
                )

                output.append(result.content)

            else:
                result = lit_config.SUMMARIZE_CHAT.invoke(
                    lit_prompts.category_summary_chat_prompt.format_prompt(
                        question=user_question, category=current_category, content=text_to_summarize
                    ).to_messages()
                )

                output.append(
                    "# "
                    + str(current_category)
                    + "\n\n"
                    + result.content
                    + "\n\n"
                    + "\n\n".join(filtered_rows.citation)
                )
    return "\n\n".join(output), response_meta


# TODO: find better place for this. Used by write_first_draft()
def extract_apa_citations(markdown_text):
    # Split the document into paragraphs
    paragraphs = markdown_text.split("\n\n")

    # Filter paragraphs that contain "PMID"
    citations = [para for para in paragraphs if "PMID" in para]
    non_citations = [para for para in paragraphs if "PMID" not in para]

    return citations, non_citations


def write_first_draft(summaries_markdown, user_question):
    citations, non_citations = extract_apa_citations(summaries_markdown)
    with get_openai_callback() as response_meta:
        introduction_result = lit_config.SUMMARIZE_CHAT.invoke(
            lit_prompts.draft_introduction_prompt.format_prompt(
                question=user_question, summaries="\n\n".join(non_citations)
            ).to_messages()
        )

        conclusion_result = lit_config.SUMMARIZE_CHAT.invoke(
            lit_prompts.draft_conclusion_prompt.format_prompt(
                question=user_question,
                summaries="\n\n".join(non_citations),
                introduction=introduction_result.content,
            ).to_messages()
        )

        abstract_result = lit_config.SUMMARIZE_CHAT.invoke(
            lit_prompts.draft_abstract_prompt.format_prompt(
                question=user_question,
                summaries="\n\n".join(non_citations),
                introduction=introduction_result.content,
                methodology=lit_boilerplate.METHODOLOGY,
                conclusion=conclusion_result.content,
            ).to_messages()
        )

    assembled_draft = (
        abstract_result.content
        + "\n\n"
        + introduction_result.content
        + "\n\n"
        + lit_boilerplate.METHODOLOGY
        + "\n\n"
        + "# Results/Discussion \n\n"
        + "\n\n".join(non_citations)
        + "\n\n"
        + conclusion_result.content
        + "\n\n"
        + "# References \n\n"
        + "\n\n".join(citations)
    )

    return assembled_draft, response_meta


def generate_keywords(df, research_question):
    relevant_rows = review_data.get_relevant_rows(df)
    all_keywords = []
    for keywords in relevant_rows["keywords"]:
        keywords_list = [keyword.strip().lower() for keyword in keywords.split(",")]
        clean_keywords_list = review_data.clean_keywords(keywords_list)
        all_keywords +=clean_keywords_list 
    all_keywords = list(set(all_keywords))
    all_titles = []
    for title in relevant_rows["title"]:
        titles_list = review_data.clean_title(title)
        all_titles += titles_list
    all_titles = list(set(all_titles))
    formatted_prompt = lit_prompts.keyword_chat_prompt.format_prompt(
        question=research_question, titles=all_titles, keywords_list=all_keywords
    )
    with get_openai_callback() as response_meta:
        result = lit_config.CHAT35.invoke(formatted_prompt.to_messages())

    print("Result - ", result)
    return result.content, response_meta
