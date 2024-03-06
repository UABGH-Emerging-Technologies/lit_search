import pandas as pd
import tempfile

def make_downloadable_excel(local_file, df, sheet2_text=None):
    with pd.ExcelWriter(local_file.name, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # Define a format with word wrap
        wrap_format = workbook.add_format({'text_wrap': True})

        # Iterate over the DataFrame columns to set the column width
        for idx, col in enumerate(df.columns):
            # Find the maximum length of data in the column
            column_len = df[col].astype(str).map(len).max()
            column_title_len = len(col)
            max_len = min(100, max(column_len, column_title_len))

            # Set the column width with some extra margin
            worksheet.set_column(idx, idx, max_len + 1, wrap_format)
