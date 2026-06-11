#!/bin/bash

cd /workspaces/ScopingReview/src
pip install --upgrade pip setuptools wheel\
	    && pip install -e ".[dev]"
