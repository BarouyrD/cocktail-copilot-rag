#!/bin/bash
set -e

echo "Initializing database tables..."
python cocktail_assistant/db_init.py

echo "Starting Streamlit..."
exec streamlit run cocktail_assistant/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0
