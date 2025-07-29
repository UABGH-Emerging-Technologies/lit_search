#!/bin/bash

python3 -m pip install pip setuptools wheel
python3 -m pip install -e "."

python3 app/server.py