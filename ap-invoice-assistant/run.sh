#!/usr/bin/env bash
set -e
python3 -m pip install -r requirements.txt --quiet
python3 sample_data/generate_sample_invoice.py
streamlit run app.py
