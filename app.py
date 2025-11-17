import os
import streamlit as st
from datetime import datetime
import yfinance as yf
from openai import OpenAI

# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="NOVA",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

hide_sidebar = """
<style>
    [data-testid="collapsedControl"] {display: none;}
    section[data-testid="stSidebar"] {display: none;}
</style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)

# =========================================================
# OPENAI CLIENT
# =========================================================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# =========================================================
# STOCK PRICE FUNCTION (FIXED)
# =========================================================
def fetch_stock_price(ticker):
    try:
        data = yf.download(ticker, period="1d", progress=False)
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except:
        return None

# =========================================================
# NOVA CHAT LOGIC
# =========================================================
def nova_reply(user_input):

    # Handle email-related requests (since email is not integrated)
    email_keywords = ["email", "inbox", "gmail", "messages", "unread"]
    if any(word in user_input.lower() for word in email_keywords):
        return "I can talk about anything you want, but I don’t have live access to email or inbox data."

    # Handle stock questions
    if "stock" in user_input.lower():
        words = user_input.upper().split()
        ticker = None

        for w in words:
            if w.isalpha() and len(w) <= 5:
                ticker = w
                break

        if ticker:
            price = fetch_stock_price(ticker)
            if price:
                return f"{ticker} is currently trading at **${price:,.2f}**."
            else:
                return f"I couldn’t pull data for **{ticker}** right now."

    # General answer using OpenAI
    ai = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Your name is Nova. Keep replies short, smart, and conversational."},
            {"role": "user", "content": user_input}
        ]
    )

    return ai.choices[0].message.content


# =========================================================
# UI
# =========================================================
st.markdown("<h1 style='color:#d7ffce; font-size:50px;'>✨ NOVA</h1>", unsafe_allow_html=True)

user = st.chat_input("Ask Nova something...")

if user:
    st.chat_message("user", avatar="🔴").write(user)
    reply = nova_reply(user)
    st.chat_message("assistant", avatar="🟧").write(reply)
