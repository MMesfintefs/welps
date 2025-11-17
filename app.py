import streamlit as st
from openai import OpenAI

client = OpenAI()

st.title("Simple AI Demo ")
user_input = st.text_input("Type something:")

if user_input:
    response = client.responses.create(
        model="gpt-5.1",
        input=user_input
    )

    st.subheader("Response:")
    st.write(response.output_text)
