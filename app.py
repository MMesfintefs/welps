# =========================================================
# NOVA – Stocks + Budget Travel Planner
# =========================================================

import os
import re

import streamlit as st
import yfinance as yf
from openai import OpenAI

# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="NOVA",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide sidebar toggle
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 style='font-size:52px; color:#d2ffd0;'>✨ NOVA</h1>"
    "<p style='color:#b8f7c4;'>Stocks & smart trip planning. Ask things like "
    "<code>price of AAPL</code> or "
    "<code>Plan a 3-day NYC trip for $400</code>.</p>",
    unsafe_allow_html=True,
)

# =========================================================
# OPENAI CLIENT
# =========================================================
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None


# =========================================================
# STOCK HELPERS
# =========================================================

# Simple mapping so "amazon stock" etc still work
NAME_TO_TICKER = {
    "AMAZON": "AMZN",
    "APPLE": "AAPL",
    "TESLA": "TSLA",
    "GOOGLE": "GOOG",
    "ALPHABET": "GOOG",
    "MICROSOFT": "MSFT",
    "META": "META",
    "FACEBOOK": "META",
    "NVIDIA": "NVDA",
}

def extract_ticker(text: str) -> str | None:
    upper = text.upper()

    # First check common names
    for name, symbol in NAME_TO_TICKER.items():
        if name in upper:
            return symbol

    # Then look for probable ticker symbols (1–5 letters)
    candidates = re.findall(r"\b[A-Z]{1,5}\b", upper)
    blacklist = {"STOCK", "PRICE", "OF", "FOR", "AND", "USD"}
    for c in candidates:
        if c not in blacklist:
            return c

    return None


def fetch_stock_history(ticker: str):
    # 1 month of daily data
    data = yf.download(ticker, period="1mo", progress=False)
    if data is None or data.empty:
        return None
    return data


def handle_stock_query(user_text: str):
    ticker = extract_ticker(user_text)
    if not ticker:
        return "I couldn’t figure out which ticker you meant. Try something like `AAPL`, `TSLA`, or `NVDA`."

    data = fetch_stock_history(ticker)
    if data is None:
        return f"No data available for **{ticker}** right now."

    last_close = float(data["Close"].iloc[-1])

    with st.chat_message("assistant"):
        st.markdown(f"### 📈 {ticker} stock\nLast close: **${last_close:,.2f}**")
        st.line_chart(data["Close"])

    # We already wrote inside the chat_message, so return None to skip double printing
    return None


# =========================================================
# TRAVEL / BUDGET PLANNER
# =========================================================

TRAVEL_KEYWORDS = [
    "trip",
    "travel",
    "vacation",
    "weekend",
    "getaway",
    "places to eat",
    "where to eat",
    "where to stay",
    "hotel",
    "airbnb",
    "things to do",
    "what to do",
    "itinerary",
    "visit",
]

def extract_budget(text: str) -> int | None:
    # Grab the largest number in the text as the budget (simple but works)
    nums = re.findall(r"\$?(\d+)", text.replace(",", ""))
    if not nums:
        return None
    return int(max(nums))


def handle_travel_query(user_text: str):
    if client is None:
        return "Travel planning works only when OPENAI_API_KEY is configured."

    budget = extract_budget(user_text)
    budget_str = f"${budget}" if budget else "the budget you think is reasonable"

    system_prompt = (
        "You are NOVA, a concise travel & budget planner. "
        "User will ask for places to eat, stay, and visit in some location, usually with a budget. "
        "Use the given budget as TOTAL for the trip if they mention one. "
        f"If no budget is clear, assume {budget_str}. "
        "Return a clear, structured answer with these sections:\n"
        "1) Summary (1–2 sentences)\n"
        "2) Where to stay (2–3 options, with nightly price ranges)\n"
        "3) Where to eat (mix of cheap + midrange, with rough cost per meal)\n"
        "4) Things to do (free + paid, with rough costs)\n"
        "Keep it realistic, grounded, and within budget. "
        "Use bullet points, no tables."
    )

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )

    return completion.choices[0].message.content


# =========================================================
# GENERIC CHAT
# =========================================================

def handle_general_chat(user_text: str):
    if client is None:
        return "AI chat only works when OPENAI_API_KEY is configured."

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NOVA, a helpful but concise assistant. "
                    "If the user didn't ask about stocks or travel, just answer normally in 2–4 sentences."
                ),
            },
            {"role": "user", "content": user_text},
        ],
    )

    return completion.choices[0].message.content


# =========================================================
# MAIN INPUT / ROUTING
# =========================================================

user_input = st.chat_input("Ask NOVA about stocks or trip planning…")

if user_input:
    st.chat_message("user").write(user_input)
    lower = user_input.lower()

    # 1. Stocks
    if any(word in lower for word in ["stock", "price", "ticker", "share"]):
        result = handle_stock_query(user_input)
        if result is not None:
            st.chat_message("assistant").markdown(result)

    # 2. Travel / budget planning
    elif any(word in lower for word in TRAVEL_KEYWORDS):
        reply = handle_travel_query(user_input)
        st.chat_message("assistant").markdown(reply)

    # 3. Fallback: general chat
    else:
        reply = handle_general_chat(user_input)
        st.chat_message("assistant").markdown(reply)
