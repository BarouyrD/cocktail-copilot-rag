import csv
import string

import requests
import numpy as np
from minsearch import Index, VectorSearch


API_URL = "https://www.thecocktaildb.com/api/json/v1/1/search.php"

TEXT_FIELDS = ["name", "category", "glass", "instructions", "ingredients"]
KEYWORD_FIELDS = ["alcoholic"]

DATA_PATH = "data/cocktails.csv"


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


def fetch_cocktails():
    documents = []
    seen = set()

    for letter in string.ascii_lowercase:
        response = requests.get(API_URL, params={"f": letter})
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

    return documents


def save_data(documents, path=DATA_PATH):
    fieldnames = [
        "id", "name", "category", "alcoholic", "glass",
        "instructions", "ingredients", "measures", "tags",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(documents)


def load_data(path=DATA_PATH):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        documents = [dict(row) for row in reader]

    for doc in documents:
        doc["id"] = str(doc["id"])

    return documents


def build_index(documents):
    index = Index(
        text_fields=TEXT_FIELDS,
        keyword_fields=KEYWORD_FIELDS,
    )
    index.fit(documents)
    return index


def doc_to_text(doc):
    return f"{doc['name']}. {doc['ingredients']}. {doc['instructions']}"


def build_vector_index(documents, embedder, batch_size=50):
    texts = [doc_to_text(doc) for doc in documents]

    vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        vectors.extend(embedder.encode_batch(batch))

    X = np.array(vectors)

    index = VectorSearch(keyword_fields=KEYWORD_FIELDS)
    index.fit(X, documents)
    return index


if __name__ == "__main__":
    documents = fetch_cocktails()
    save_data(documents)
    print(f"Saved {len(documents)} cocktails to {DATA_PATH}")
