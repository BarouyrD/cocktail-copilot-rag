"""Airflow DAG that ingests cocktail data from TheCocktailDB into a CSV.

This DAG is self-contained (it only relies on `requests`, which ships with
Airflow) so the ingestion stack stays independent from the main application.
"""

import csv
import string
from datetime import datetime

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator


API_URL = "https://www.thecocktaildb.com/api/json/v1/1/search.php"
OUTPUT_PATH = "/opt/airflow/data/cocktails.csv"

FIELDNAMES = [
    "id", "name", "category", "alcoholic", "glass",
    "instructions", "ingredients", "measures", "tags",
]


def parse_drink(drink):
    ingredients = []
    measures = []

    for i in range(1, 16):
        ingredient = drink.get(f"strIngredient{i}")
        measure = drink.get(f"strMeasure{i}")

        if ingredient and ingredient.strip():
            ingredients.append(ingredient.strip())
            measures.append((measure or "").strip())

    return {
        "id": str(drink["idDrink"]),
        "name": drink.get("strDrink") or "",
        "category": drink.get("strCategory") or "",
        "alcoholic": drink.get("strAlcoholic") or "",
        "glass": drink.get("strGlass") or "",
        "instructions": drink.get("strInstructions") or "",
        "ingredients": ", ".join(ingredients),
        "measures": ", ".join(measures),
        "tags": drink.get("strTags") or "",
    }


def ingest_cocktails():
    documents = []
    seen = set()

    for letter in string.ascii_lowercase:
        response = requests.get(API_URL, params={"f": letter}, timeout=30)
        response.raise_for_status()
        drinks = response.json().get("drinks")

        if not drinks:
            continue

        for drink in drinks:
            doc = parse_drink(drink)
            if doc["id"] in seen:
                continue
            seen.add(doc["id"])
            documents.append(doc)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(documents)

    print(f"Saved {len(documents)} cocktails to {OUTPUT_PATH}")


with DAG(
    dag_id="ingest_cocktails",
    start_date=datetime(2024, 1, 1),
    schedule="@weekly",
    catchup=False,
    tags=["cocktails"],
) as dag:
    PythonOperator(
        task_id="ingest_cocktails",
        python_callable=ingest_cocktails,
    )
