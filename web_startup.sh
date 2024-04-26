#!/bin/bash

#if weird dns errors, try
#cp -f ./resolv.conf /etc/resolv.conf

streamlit run streamlit/ScopingReview_app.py --server.port=8501 --server.address=0.0.0.0