import sys

from dotenv import load_dotenv
from openai import OpenAI

from ingest import load_data, build_index, build_vector_index
from embedder import Embedder
from metrics import RAGWithMetrics
from db_save import save_conversation

COURSE = "cocktails"


def create_assistant():
    load_dotenv()

    documents = load_data()
    text_index = build_index(documents)

    embedder = Embedder()
    vector_index = build_vector_index(documents, embedder)

    return RAGWithMetrics(
        index=text_index,
        vector_index=vector_index,
        embedder=embedder,
        llm_client=OpenAI(),
    )


if __name__ == "__main__":
    assistant = create_assistant()

    query = "What's in a Margarita?"
    if len(sys.argv) > 1:
        query = sys.argv[1]

    answer = assistant.rag(query)
    print(answer)

    save_conversation(assistant.last_call, query, COURSE)
