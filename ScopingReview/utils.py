import calendar
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests


def make_downloadable_excel(local_file, df, sheet2_text=None):
    with pd.ExcelWriter(local_file.name, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")

        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        # Define a format with word wrap
        wrap_format = workbook.add_format({"text_wrap": True})

        # Iterate over the DataFrame columns to set the column width
        for idx, col in enumerate(df.columns):
            # Find the maximum length of data in the column
            column_len = df[col].astype(str).map(len).max()
            column_title_len = len(col)
            max_len = min(100, max(column_len, column_title_len))

            # Set the column width with some extra margin
            worksheet.set_column(idx, idx, max_len + 1, wrap_format)


def pmid2bibtex(pmids: list):
    ## Adapted from: https://gist.github.com/tommycarstensen/ec3c57761f3846c339de925b66f4ac1b
    ## Fetch XML data from Entrez.
    efetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    r = requests.get("{}?db=pubmed&id={}&rettype=abstract".format(efetch, ",".join(pmids)))
    ##print(r.text)

    ## Loop over the PubMed IDs and parse the XML.
    root = ET.fromstring(r.text)
    whole_bibtex = ""
    for PubmedArticle in root.iter("PubmedArticle"):
        PMID = PubmedArticle.find("./MedlineCitation/PMID")
        ISSN = PubmedArticle.find("./MedlineCitation/Article/Journal/ISSN")
        Volume = PubmedArticle.find("./MedlineCitation/Article/Journal/JournalIssue/Volume")
        Issue = PubmedArticle.find("./MedlineCitation/Article/Journal/JournalIssue/Issue")
        Year = PubmedArticle.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate/Year")
        Month = PubmedArticle.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate/Month")
        Title = PubmedArticle.find("./MedlineCitation/Article/Journal/Title")
        ArticleTitle = PubmedArticle.find("./MedlineCitation/Article/ArticleTitle")
        MedlinePgn = PubmedArticle.find("./MedlineCitation/Article/Pagination/MedlinePgn")
        Abstract = PubmedArticle.find("./MedlineCitation/Article/Abstract/AbstractText")
        authors = []
        for Author in PubmedArticle.iter("Author"):
            try:
                LastName = Author.find("LastName").text
                ForeName = Author.find("ForeName").text
            except AttributeError:  # e.g. CollectiveName
                continue
            authors.append("{}, {}".format(LastName, ForeName))
        if Year is None:
            _ = PubmedArticle.find(
                "./MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate"
            )
            print("Debugging: _.text is", _.text)
            Year = _.text[:4]

            month_abbr = ""
            for month in calendar.month_abbr:
                if _.text[5:8] in month:
                    month_abbr = month[:3]
                    break

            Month = "{:02d}".format(list(calendar.month_abbr).index(month_abbr))

        else:
            Year = Year.text
            if Month is not None:
                Month = Month.text
        try:
            for _ in (
                PMID.text,
                Volume.text,
                Title.text,
                ArticleTitle.text,
                MedlinePgn.text,
                Abstract.text,
                "".join(authors),
            ):
                ##        assert '"' not in _, _
                if _ is None:
                    continue
                assert "{" not in _, _
                assert "}" not in _, _
        except AttributeError:
            pass
        ## Print the bibtex formatted output.
        bibtex_fmt = ""
        try:
            line1 = "@Article{{{}{}pmid{},".format(authors[0].split(",")[0], Year, PMID.text)
            bibtex_fmt = "".join([line1, "\n"])
        except IndexError:
            print("IndexError", pmids, file=sys.stderr, flush=True)
        except AttributeError:
            print("AttributeError", pmids, file=sys.stderr, flush=True)
        line2 = ' Author="{}",'.format(" and ".join(authors))
        line3 = " Title={{{}}},".format(ArticleTitle.text)
        line4 = " Journal={{{}}},".format(Title.text)
        line5 = " Year={{{}}},".format(Year)
        bibtex_fmt = bibtex_fmt + "".join([line2, "\n", line3, "\n", line4, "\n", line5, "\n"])
        if Volume is not None:
            line6 = " Volume={{{}}},".format(Volume.text)
            bibtex_fmt = bibtex_fmt + "".join([line6, "\n"])
        if Issue is not None:
            line7 = " Number={{{}}},".format(Issue.text)
            bibtex_fmt = bibtex_fmt + "".join([line7, "\n"])
        if MedlinePgn is not None:
            line8 = " Pages={{{}}},".format(MedlinePgn.text)
            bibtex_fmt = bibtex_fmt + "".join([line8, "\n"])
        if Month is not None:
            line9 = " Month={{{}}},".format(Month)
            bibtex_fmt = bibtex_fmt + "".join([line9, "\n"])

        # line10 = ' Abstract={{{}}},'.format(Abstract.text)
        if ISSN is not None:
            line11 = " ISSN={{{}}},".format(ISSN.text)
            bibtex_fmt = bibtex_fmt + "".join([line11, "\n"])

        line12 = "}"
        bibtex_fmt = bibtex_fmt + "".join([line12])
        whole_bibtex = whole_bibtex + bibtex_fmt + "\n"
    return whole_bibtex
