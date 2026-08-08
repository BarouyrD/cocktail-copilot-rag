.PHONY: install download ingest db up down dashboard data airflow-up airflow-down

# Install dependencies
install:
	uv sync

# Download the ONNX embedding model into models/
download:
	uv run python cocktail_assistant/download.py

# Fetch cocktail data from TheCocktailDB into data/cocktails.csv
ingest:
	uv run python cocktail_assistant/ingest.py

# Initialize the PostgreSQL tables
db:
	uv run python cocktail_assistant/db_init.py

# Start the full stack (postgres + grafana + streamlit)
up:
	docker-compose up --build

down:
	docker-compose down

# Run the Streamlit monitoring dashboard locally
dashboard:
	uv run streamlit run cocktail_assistant/dashboard.py

# Pump synthetic conversations into the database
data:
	uv run python cocktail_assistant/generate_data.py

# Start / stop the standalone Airflow ingestion stack
airflow-up:
	docker-compose -f airflow/docker-compose.airflow.yaml up

airflow-down:
	docker-compose -f airflow/docker-compose.airflow.yaml down
