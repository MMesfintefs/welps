import os
import re
import streamlit as st
import yfinance as yf
from openai import OpenAI

# ------------------------------------------------
# Page Setup
# ------------------------------------------------
st.set_page_config(page_title="NOVA", page_icon="✨", layout="wide")
st.title("✨ NOVA")

# ------------------------------------------------
# Load OpenAI Key
# ------------------------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", None)

if OPENAI_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    client = OpenAI()
else:
    client = None

# ------------------------------------------------
# Stock Lookup (no try/except)
# ------------------------------------------------
def lookup_stock(ticker: str):
    data = yf.Ticker(ticker).history(period="1d")
    if data.empty:
        return None
    return float(data["Close"].iloc[-1])


def handle_stocks(text):
    tickers = re.findall(r"\b[A-Z]{2,5}\b", text.upper())
    tickers = [t for t in tickers if t not in ["OF", "THE"]]

    if not tickers:
        return "I didn’t find any valid stock tickers."

    output = "📊 **Stock Prices**\n\n"
    for t in tickers:
        price = lookup_stock(t)
        if price:
            output += f"• **{t}** — ${price:.2f}\n"
        else:
            output += f"• **{t}** — No data available\n"

    return output


# ------------------------------------------------
# Email Question Fallback (no API access)
# ------------------------------------------------
EMAIL_QUESTIONS = [
    "email",
    "inbox",
    "did i get",
    "did i receive",
    "new messages",
    "new email",
    "check mail",
    "check my email"
]

def handle_email_fallback():
    return (
        "📬 I don’t have access to your inbox right now, "
        "but you can check your Gmail app to see any recent messages."
    )


# ------------------------------------------------
# OpenAI Chat
# ------------------------------------------------
def chat_with_openai(message):
    if client is None:
        return "AI not configured (missing OPENAI_API_KEY)."

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}]
    )

    return completion.choices[0].message.content


# ------------------------------------------------
# MAIN CHAT INPUT
# ------------------------------------------------
user_input = st.chat_input("Ask NOVA…")

if user_input:

    # show user message
    with st.chat_message("user"):
        st.write(user_input)

    lower_msg = user_input.lower()

    # 1. Stock commands
    if any(w in lower_msg for w in ["price", "stock", "check", "market"]):
        with st.chat_message("assistant"):
            st.write(handle_stocks(user_input))

    # 2. Email related questions
    elif any(w in lower_msg for w in EMAIL_QUESTIONS):
        with st.chat_message("assistant"):
            st.write(handle_email_fallback())

    # 3. Normal chat (OpenAI)
    else:
        with st.chat_message("assistant"):
            st.write(chat_with_openai(user_input))
