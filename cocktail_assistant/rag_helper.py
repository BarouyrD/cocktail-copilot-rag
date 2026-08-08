INSTRUCTIONS = """
You are a helpful cocktail assistant. Answer the user's question using
only the cocktail information provided in the context.

Use the context to find relevant recipes, ingredients, and instructions.
If the answer is not found in the context, respond with "I don't know."
""".strip()

# Alternative prompt variant, compared against INSTRUCTIONS in notebook 04.
INSTRUCTIONS_MIXOLOGIST = """
You are an expert mixologist with years of experience behind the bar.
Answer the user's question in a friendly, knowledgeable tone, based only
on the cocktail information provided in the context.

Mention ingredients, measures, and preparation steps when they are helpful.
If the answer is not found in the context, honestly say you don't know
instead of inventing a recipe.
""".strip()

PROMPT_TEMPLATE = """
QUESTION: {question}

COCKTAILS:
{context}
""".strip()


class RAGBase:

    def __init__(
        self,
        index,
        llm_client,
        instructions=INSTRUCTIONS,
        prompt_template=PROMPT_TEMPLATE,
        model="gpt-5.4-mini",
    ):
        self.index = index
        self.llm_client = llm_client
        self.instructions = instructions
        self.prompt_template = prompt_template
        self.model = model

    def search(self, query, num_results=5):
        boost_dict = {"name": 3.0, "ingredients": 2.0, "category": 0.5}

        return self.index.search(
            query,
            num_results=num_results,
            boost_dict=boost_dict,
        )

    def build_context(self, search_results):
        lines = []

        for doc in search_results:
            lines.append(f"Name: {doc['name']}")
            lines.append(f"Category: {doc['category']} ({doc['alcoholic']})")
            lines.append(f"Glass: {doc['glass']}")
            lines.append(f"Ingredients: {doc['ingredients']}")
            lines.append(f"Measures: {doc['measures']}")
            lines.append(f"Instructions: {doc['instructions']}")
            lines.append("")

        return "\n".join(lines).strip()

    def build_prompt(self, query, search_results):
        context = self.build_context(search_results)
        return self.prompt_template.format(
            question=query, context=context
        )

    def llm(self, prompt):
        input_messages = [
            {"role": "developer", "content": self.instructions},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_client.responses.create(
            model=self.model,
            input=input_messages
        )

        return response.output_text

    def rag(self, query):
        search_results = self.search(query)
        prompt = self.build_prompt(query, search_results)
        answer = self.llm(prompt)
        return answer


class RAGVector(RAGBase):

    def __init__(self, embedder, **kwargs):
        super().__init__(**kwargs)
        self.embedder = embedder

    def search(self, query, num_results=5):
        query_vector = self.embedder.encode(query)

        return self.index.search(
            query_vector,
            num_results=num_results,
        )


class RAGHybrid(RAGBase):

    def __init__(self, vector_index, embedder, k=60, **kwargs):
        super().__init__(**kwargs)
        self.vector_index = vector_index
        self.embedder = embedder
        self.k = k

    def text_search(self, query, num_results=10):
        boost_dict = {"name": 3.0, "ingredients": 2.0, "category": 0.5}

        return self.index.search(
            query,
            num_results=num_results,
            boost_dict=boost_dict,
        )

    def vector_search(self, query, num_results=10):
        query_vector = self.embedder.encode(query)
        return self.vector_index.search(query_vector, num_results=num_results)

    def search(self, query, num_results=5):
        text_results = self.text_search(query)
        vector_results = self.vector_search(query)

        scores = {}
        docs = {}

        for rank, doc in enumerate(text_results):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (self.k + rank + 1)
            docs[doc_id] = doc

        for rank, doc in enumerate(vector_results):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (self.k + rank + 1)
            docs[doc_id] = doc

        ranked_ids = sorted(scores, key=scores.get, reverse=True)
        return [docs[doc_id] for doc_id in ranked_ids[:num_results]]
