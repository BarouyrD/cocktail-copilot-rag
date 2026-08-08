import time
import random

from metrics import LLMCallRecord
from db_save import save_conversation
from db_feedback import save_feedback

COURSE = "cocktails"

SAMPLE_QUESTIONS = [
    "What's in a Margarita?",
    "How do I make a Mojito?",
    "Suggest a non-alcoholic cocktail.",
    "Which glass is used for a Martini?",
    "What ingredients go into a Negroni?",
    "Give me a rum-based cocktail.",
]

SAMPLE_ANSWERS = [
    "A Margarita is made with tequila, triple sec, and lime juice, served in a cocktail glass.",
    "Muddle mint with sugar and lime, add white rum and soda water, then serve over ice.",
    "Try a Virgin Mojito: mint, lime, sugar, and soda water, with no alcohol.",
    "A Martini is traditionally served in a chilled cocktail (martini) glass.",
    "A Negroni combines equal parts gin, Campari, and sweet vermouth.",
    "A Daiquiri uses white rum, lime juice, and simple syrup, shaken and strained.",
]

RELEVANCE = ["RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT"]


def fake_record(question, answer):
    return LLMCallRecord(
        model="gpt-5.4-mini",
        prompt=question,
        instructions="",
        answer=answer,
        prompt_tokens=random.randint(50, 200),
        completion_tokens=random.randint(50, 300),
        total_tokens=random.randint(100, 500),
        response_time=random.uniform(0.5, 5.0),
        cost=random.uniform(0.0001, 0.01),
    )


def random_score():
    return random.choice([1, 1, 1, 1, -1])


def generate_one():
    question = random.choice(SAMPLE_QUESTIONS)
    answer = random.choice(SAMPLE_ANSWERS)
    record = fake_record(question, answer)

    conversation_id = save_conversation(record, question, COURSE)

    if random.random() < 0.7:
        relevance = random.choice(RELEVANCE)
        save_feedback(
            conversation_id, "judge",
            relevance=relevance,
            explanation=f"Answer is {relevance.lower()}.",
        )

    if random.random() < 0.5:
        score = random_score()
        save_feedback(conversation_id, "user", score=score)


def generate_live():
    print("Starting live data generation (Ctrl+C to stop)...", flush=True)
    while True:
        generate_one()
        time.sleep(1)


if __name__ == "__main__":
    try:
        generate_live()
    except KeyboardInterrupt:
        print("Stopped.")
