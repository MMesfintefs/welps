import os, requests, statistics
import yfinance as yf
from textblob import TextBlob

# ---------- CREDIBLE NEWS FETCH ----------
def get_finance_news(topic="markets"):
    """
    Fetch recent credible financial headlines from selected domains via NewsAPI.
    Sources: Bloomberg, Reuters, WSJ, CNBC, MarketWatch.
    """
    key = os.getenv("NEWSAPI_API_KEY")
    if not key:
        return [
            {"title": "Stocks mixed as investors eye inflation data", "source": "Reuters"},
            {"title": "Tech gains offset energy losses", "source": "Bloomberg"},
            {"title": "Fed policy hints support cautious optimism", "source": "CNBC"},
        ]
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": topic,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 8,
            "domains": "bloomberg.com,reuters.com,wsj.com,cnbc.com,marketwatch.com",
        }
        headers = {"X-Api-Key": key}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        return [
            {"title": a["title"], "source": a["source"]["name"]}
            for a in data.get("articles", [])[:8]
        ]
    except Exception:
        return [{"title": "Unable to fetch latest headlines.", "source": "System"}]

# ---------- SENTIMENT + VIX MOOD ----------
def get_vix_score():
    """Compute calmness from volatility (inverse relationship)."""
    try:
        vix = yf.Ticker("^VIX").history(period="5d")["Close"].iloc[-1]
        score = max(0, min(100, 100 - (vix * 2)))  # low VIX = calmer = bullish
        return round(score, 1)
    except Exception:
        return 50

def get_headline_sentiment(news_list):
    """Average polarity of news headlines using TextBlob."""
    sentiments = []
    for n in news_list:
        blob = TextBlob(n["title"])
        sentiments.append(blob.sentiment.polarity)
    if not sentiments:
        return 50
    avg = statistics.mean(sentiments)
    return round((avg + 1) * 50, 1)  # scale -1..1 → 0..100

def compute_market_mood(news_list):
    """Weighted blend of headline tone (60%) + volatility calmness (40%)."""
    return round(
        (get_vix_score() * 0.4 + get_headline_sentiment(news_list) * 0.6), 1
    )

# ---------- DECISION SIGNAL ----------
def rsi(series, period=14):
    """Relative Strength Index calculation."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def decision_signal(hist_df):
    """Generate buy/hold/sell style guidance from RSI + price change."""
    hist_df["RSI"] = rsi(hist_df["close"])
    rsi_last = hist_df["RSI"].iloc[-1]
    change = (
        (hist_df["close"].iloc[-1] - hist_df["close"].iloc[-2])
        / hist_df["close"].iloc[-2]
    ) * 100
    if change < -2 and rsi_last < 30:
        return "📉 Oversold — potential rebound zone"
    elif change > 2 and rsi_last > 70:
        return "📈 Overbought — consider trimming"
    elif abs(change) < 0.3:
        return "⚖️ Flat momentum — neutral zone"
    else:
        return "💤 Stable / Hold"
