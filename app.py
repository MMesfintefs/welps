import os
import re
import streamlit as st
import yfinance as yf
from openai import OpenAI

# ------------------------------------
# Page Setup
# ------------------------------------
st.set_page_config(page_title="NOVA", page_icon="✨")
st.title("✨ NOVA ")

# ------------------------------------
# OpenAI Key
# ------------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", None)

if OPENAI_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    client = OpenAI()
else:
    client = None

# ------------------------------------
# Sidebar
# ------------------------------------
st.sidebar.title("Commands")
st.sidebar.subheader("Stocks")
st.sidebar.write("• price of AAPL")
st.sidebar.write("• check TSLA and MSFT")

st.sidebar.subheader("Chat")
st.sidebar.write("• ask anything")

# ------------------------------------
# Stock Lookup — ZERO try/except
# ------------------------------------
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

# ------------------------------------
# OpenAI Chat — ZERO try blocks
# ------------------------------------
def chat_with_openai(message):
    if client is None:
        return "AI not configured (missing OPENAI_API_KEY)."

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}]
    )
    return completion.choices[0].message.content

# ------------------------------------
# Main Chat Input
# ------------------------------------
user_input = st.chat_input("Ask NOVA…")

if user_input:

    with st.chat_message("user"):
        st.write(user_input)

    # stock rule
    if any(w in user_input.lower() for w in ["price", "stock", "check"]):
        with st.chat_message("assistant"):
            st.write(handle_stocks(user_input))

    # chat rule
    else:
        with st.chat_message("assistant"):
            st.write(chat_with_openai(user_input))
