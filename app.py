import os
import streamlit as st
from openai import OpenAI
import yfinance as yf

from gmail_calendar import read_last_5_emails, get_calendar_events

# ------------------- Load Secrets -------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_KEY)

# ------------------- Streamlit UI -------------------
st.set_page_config(page_title="NOVA", page_icon="✨", layout="wide")

st.title("✨ NOVA — Your Personal AI Assistant")

# ------------------- Core Agent Brain -------------------
def nova_reply(user_message):
    """
    NOVA interprets natural language and decides what to do.
    """

    # 1. Check for Gmail commands
    if "email" in user_message.lower():
        try:
            emails = read_last_5_emails()
            return "\n\n".join([f"- {e}" for e in emails])
        except Exception as e:
            return f"Email error: {e}"
    
    # 2. Calendar commands
    if "calendar" in user_message.lower() or "event" in user_message.lower():
        try:
            events = get_calendar_events()
            return "\n\n".join(events)
        except Exception as e:
            return f"Calendar error: {e}"

    # 3. Stock lookup
    if "stock" in user_message.lower() or "price" in user_message.lower():
        words = user_message.upper().split()
        tickers = [w for w in words if w.isalpha() and len(w) <= 5]

        if not tickers:
            return "Which stock symbol do you want? (Example: AAPL, TSLA, MSFT)"

        output = []
        for t in tickers:
            try:
                data = yf.Ticker(t).history(period="1d")
                price = data["Close"].iloc[-1]
                output.append(f"{t} → ${price:.2f}")
            except:
                output.append(f"{t} → not found")

        return "\n".join(output)

    # 4. Fall back to OpenAI conversation
    try:
        completion = client.responses.create(
            model="gpt-4.1-mini",
            input=user_message
        )
        return completion.output_text
    except Exception as e:
        return f"AI error: {e}"

# ------------------- Chat Interface -------------------
user_input = st.chat_input("Ask Nova anything...")

if user_input:
    st.chat_message("user").write(user_input)
    response = nova_reply(user_input)
    st.chat_message("assistant").write(response)
