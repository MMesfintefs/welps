# =========================================================
# NOVA – Minimal Agentic Assistant (Mock Email + Stocks)
# =========================================================

import os
import streamlit as st
import yfinance as yf
from openai import OpenAI

# =========================================================
# SETUP
# =========================================================
st.set_page_config(
    page_title="NOVA",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
        /* Hide sidebar completely */
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}

        /* Chat styling */
        .nova-input input {
            background: #111;
            color: #fff;
            border-radius: 8px;
            border: 1px solid #333;
            padding: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# OPENAI CLIENT
# =========================================================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================================================
# MOCK EMAIL INBOX
# =========================================================
mock_emails = [
    {
        "sender": "Professor Li",
        "subject": "Reminder: Exam Review Tomorrow",
        "hours_ago": 1
    },
    {
        "sender": "UPS",
        "subject": "Your package has shipped",
        "hours_ago": 3
    },
    {
        "sender": "Bentley Student Services",
        "subject": "Important Financial Aid Update",
        "hours_ago": 5
    }
]


# =========================================================
# STOCK DATA
# =========================================================
def fetch_stock_price(ticker):
    try:
        data = yf.download(ticker, period="1d", progress=False)
        if data is None or data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except:
        return None


# =========================================================
# NOVA LOGIC
# =========================================================
def nova_reply(user_input):

    txt = user_input.lower()

    # Email trigger
    email_triggers = [
        "email", "emails", "gmail", "inbox", "messages",
        "new emails", "past few hours", "check email"
    ]

    if any(t in txt for t in email_triggers):
        out = "Here’s what’s in your inbox:\n\n"
        for e in mock_emails:
            out += (
                f"📨 **{e['hours_ago']} hrs ago — {e['sender']}**\n"
                f"• *{e['subject']}*\n\n"
            )
        return out

    # Stock trigger
    if "stock" in txt or "price" in txt:
        words = user_input.upper().split()
        ticker = None
        for w in words:
            if w.isalpha() and len(w) <= 5:
                ticker = w
                break

        if ticker:
            price = fetch_stock_price(ticker)
            if price:
                return f"**{ticker}** is currently trading at **${price:,.2f}**."
            else:
                return f"No stock data available for **{ticker}**."

    # Normal conversation (OpenAI)
    ai = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Your name is Nova. Keep replies short, clear, and warm."},
            {"role": "user", "content": user_input}
        ]
    )
    return ai.choices[0].message.content


# =========================================================
# UI
# =========================================================
st.markdown(
    "<h1 style='font-size:52px; color:#d2ffd0;'>✨ NOVA</h1>",
    unsafe_allow_html=True
)

user_text = st.chat_input("Ask Nova something...", key="nova", autocomplete=False)

if user_text:
    st.chat_message("user").write(user_text)
    reply = nova_reply(user_text)
    st.chat_message("assistant").write(reply)
