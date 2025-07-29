import calendar
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Union

import pandas as pd
import requests
from fastapi import HTTPException
from fastapi.responses import Response

import streamlit as st
from ScopingReview.BaseManager import BaseManager
from ScopingReview_config import config


class BibliographyManager(BaseManager):
    def __init__(self, file_contents, file_ext):
        self.file_contents = file_contents
        self.file_ext = file_ext
        if file_contents is not None:
            self.df = file_contents

    def get_filename(self):
        return config.SR_STEP6_FILENAME

    def _get_PMID_list(self):
        if self.file_ext == ".xlsx":
            if "PMID" in self.df.columns:
                return self.df["PMID"].astype(str).tolist()
            else:
                raise ValueError("PMIDs missing.")
        elif self.file_ext == ".docx":
            df = self.extract_docx_pmids(self.file_contents)
            if "PMID" in df.columns:
                return df["PMID"].astype(str).tolist()
            else:
                raise ValueError("Bibliography not in expected format.")

    def _pmid2bibtex(self, pmids: list):
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
            Month = PubmedArticle.find(
                "./MedlineCitation/Article/Journal/JournalIssue/PubDate/Month"
            )
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

    def convert_pmid_to_bibtex(self):
        pmid_list = self._get_PMID_list()
        if not pmid_list:
            raise ValueError("No PMIDs found to convert to BibTeX.")
        bibtex_text = self._pmid2bibtex(pmid_list)
        return bibtex_text


class StreamlitBibtexManager(BibliographyManager):
    def __init__(self, df, file_ext):
        super().__init__(df, file_ext)
        st.session_state["file_uploaded_bibtex"] = (
            False  # Unique file_uploaded variable for bibtex management
        )

    def get_download_button_label(self):
        return config.DOCX_DOWNLOAD_LABEL

    def _download_results(self, bibtex_text):
        st.balloons()
        st.write("Note that once you hit download, this form will reset.")
        st.download_button(
            label=self.get_download_button_label(),
            data=bibtex_text,
            file_name=self.get_filename(),
            mime="text/plain",
        )
        st.write("Thanks for playing! Please email feedback to rmelvin@uabmc.edu")


class FastAPIBibtexManager(BibliographyManager):
    def __init__(self, content: Union[pd.DataFrame, str], file_ext: str) -> Response:
        super().__init__(content, file_ext)

    def convert_and_download_bibtex(self):
        """
        Asynchronously converts PMIDs to BibTeX format and prepares it for download.
        Raises HTTPException if no PMIDs are found or if the BibTeX conversion fails.
        """
        try:
            pmid_list = self._get_PMID_list()
            if not pmid_list:
                raise ValueError("No PMIDs found to convert to BibTeX.")

            bibtex_text = self._pmid2bibtex(pmid_list)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".bib", mode="w", encoding="utf-8"
            ) as tmpfile:
                tmpfile.write(bibtex_text)
                tmpfile_name = tmpfile.name
            return tmpfile_name

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while converting PMIDs to BibTeX: {str(e)}",
            )
