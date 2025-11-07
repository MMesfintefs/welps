import yfinance as yf, requests, os
from textblob import TextBlob  # for quick sentiment
import statistics

def get_vix_score():
    try:
        vix = yf.Ticker("^VIX").history(period="5d")["Close"].iloc[-1]
        # invert volatility: lower VIX = calmer = bullish
        score = max(0, min(100, 100 - (vix * 2)))
        return round(score, 1)
    except Exception:
        return 50

def get_headline_sentiment(news_list):
    sentiments = []
    for n in news_list:
        blob = TextBlob(n["title"])
        sentiments.append(blob.sentiment.polarity)
    if not sentiments:
        return 50
    avg = statistics.mean(sentiments)
    return round((avg + 1) * 50, 1)  # scale -1..1 to 0..100

def compute_market_mood(news_list):
    return round((get_vix_score() * 0.4 + get_headline_sentiment(news_list) * 0.6), 1)
