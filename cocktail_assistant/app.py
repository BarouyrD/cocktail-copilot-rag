import streamlit as st

from assistant import create_assistant, COURSE
from db_save import save_conversation
from db_feedback import save_feedback
from judge import evaluate_relevance


@st.cache_resource
def load_assistant():
    return create_assistant()


assistant = load_assistant()

st.title("Cocktail Assistant")
st.write(
    "Ask me anything about cocktails - ingredients, recipes, "
    "glassware, and preparation steps."
)

user_input = st.text_input("Enter your question:")

if st.button("Ask") and user_input:
    with st.spinner("Mixing up an answer..."):
        answer = assistant.rag(user_input)
        record = assistant.last_call

        st.success("Done!")
        st.write(answer)

        st.write(f"Response time: {record.response_time:.2f}s")
        st.write(f"Prompt tokens: {record.prompt_tokens}")
        st.write(f"Completion tokens: {record.completion_tokens}")
        st.write(f"Cost: ${record.cost:.6f}")

        conversation_id = save_conversation(record, user_input, COURSE)
        st.session_state.conversation_id = conversation_id

        relevance, explanation = evaluate_relevance(user_input, answer)
        save_feedback(
            conversation_id, "judge",
            relevance=relevance, explanation=explanation,
        )
        st.write(f"Relevance: {relevance}")
        st.write(f"Explanation: {explanation}")


if "conversation_id" in st.session_state:
    st.subheader("Was this answer helpful?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes (+1)"):
            save_feedback(st.session_state.conversation_id, "user", score=1)
            st.write("Thanks!")
    with col2:
        if st.button("No (-1)"):
            save_feedback(st.session_state.conversation_id, "user", score=-1)
            st.write("Thanks for the feedback!")
