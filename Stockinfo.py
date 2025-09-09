import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="📊 Stock Intelligence", layout="wide")

# --- FORMATTER FUNCTIONS ---
def format_metric(key, value):
    if value is None:
        return "N/A"
    try:
        if "Yield" in key or "Return" in key or "Payout" in key or "Ratio" in key:
            return f"{value:.2%}" if value < 1 else f"{value:.2f}"
        if "Cap" in key or "Volume" in key or "Revenue" in key:
            if value >= 1_000_000_000_000:
                return f"{value / 1_000_000_000:.1f}bn"
            elif value >= 1_000_000_000:
                return f"{value / 1_000_000_000:.1f}bn"
            elif value >= 1_000_000:
                return f"{value / 1_000_000:.1f}m"
            else:
                return f"{value:,}"
        if isinstance(value, (int, float)):
            return f"{value:,.2f}"
    except:
        return value
    return value

def format_metrics_dict(metrics_dict):
    return {k: format_metric(k, v) for k, v in metrics_dict.items()}

# --- CUSTOM CALCULATIONS ---
def get_dividend_yield(info):
    dividend = info.get("trailingAnnualDividendRate")
    price = info.get("currentPrice")
    if dividend and price:
        return dividend / price
    return None

def get_payout_ratio(info):
    dividend = info.get("trailingAnnualDividendRate")
    eps = info.get("trailingEps")
    if dividend and eps and eps > 0:
        return dividend / eps
    return None

# --- METRIC FETCHING ---
def get_yfinance_metrics(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    company_name = info.get("longName", ticker.upper())
    hist = stock.history(period="1y")
    wma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
    return {
        "Valuation": {
            "Market Cap": info.get("marketCap"),
            "P/E Ratio": info.get("trailingPE"),
            "PEG Ratio": info.get("pegRatio")
        },
        "Performance": {
            "Current Price": info.get("currentPrice"),
            "200-Day WMA": round(wma_200, 2),
            "52W High": info.get("fiftyTwoWeekHigh"),
            "52W Low": info.get("fiftyTwoWeekLow"),
            "1Y Return": info.get("52WeekChange")
        },
        "Income": {
            "Dividend Yield": get_dividend_yield(info),
            "Payout Ratio": get_payout_ratio(info)
        },
        "Risk": {
            "Beta": info.get("beta"),
            "Debt/Equity": info.get("debtToEquity"),
            "Volatility": info.get("priceHint")
        }
    }

# --- FINNHUB FETCHERS ---
def get_finnhub_news(ticker, api_key):
    today = datetime.today().date()
    last_week = today - timedelta(days=7)
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={last_week}&to={today}&token={api_key}"
    return requests.get(url).json()

def get_yahoo_news(ticker):
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={ticker}"
    try:
        response = requests.get(url).json()
        articles = response.get("news", [])
        return [{"headline": a["title"], "url": a["link"]} for a in articles if "link" in a]
    except:
        return []

def get_broker_ratings(ticker, api_key):
    url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={api_key}"
    try:
        response = requests.get(url).json()
        return response[0] if isinstance(response, list) and response else {}
    except:
        return {}

def summarize_sentiment(ratings):
    if not ratings:
        return "No consensus"
    score = (
        ratings.get("strongBuy", 0) * 2 +
        ratings.get("buy", 0) * 1 +
        ratings.get("hold", 0) * 0 +
        ratings.get("sell", 0) * -1 +
        ratings.get("strongSell", 0) * -2
    )
    if score >= 10:
        return "Strong Buy"
    elif score >= 5:
        return "Moderate Buy"
    elif score >= 0:
        return "Hold"
    elif score >= -5:
        return "Moderate Sell"
    else:
        return "Strong Sell"

def get_earnings_surprises(ticker, api_key):
    url = f"https://finnhub.io/api/v1/stock/earnings?symbol={ticker}&token={api_key}"
    try:
        response = requests.get(url).json()
        return response[:5] if isinstance(response, list) else []
    except:
        return []

# --- UI ---

ticker = st.text_input("Enter Stock Ticker", "AAPL")

if ticker:
    st.markdown("---")

    # --- Badge Row ---
    stock = yf.Ticker(ticker)
    info = stock.info
    company_name = info.get("longName", ticker.upper())

    st.title(f"📈 {company_name} ({ticker.upper()})")

    price = info.get("currentPrice")
    prev_close = info.get("previousClose")
    volume = info.get("volume")
    market_cap = info.get("marketCap")
    next_earnings = info.get("earningsDate")

    if price and prev_close and volume and market_cap:
        delta = price - prev_close
        pct_change = (delta / prev_close) * 100
        cap_display = f"{market_cap / 1_000_000_000:.1f}bn"

        col1, col2, col3 = st.columns(3)
        col1.metric("📌 Share Price", f"${price:,.2f}", f"{delta:+.2f} ({pct_change:+.2f}%)")
        col2.metric("📊 Volume", f"{volume:,}")
        col3.metric("🏦 Market Cap", cap_display)

    # --- Metrics ---
    st.subheader(f"📊 Metrics for {ticker.upper()}")
    metrics = get_yfinance_metrics(ticker)
    for category, data in metrics.items():
        st.markdown(f"### 📌 {category}")
        formatted = format_metrics_dict(data)
        df = pd.DataFrame(formatted.items(), columns=["Metric", "Value"])
        st.dataframe(df, use_container_width=True)

    # --- Chart ---
    st.markdown("### 📉 Price Chart (6 Months)")
    hist = stock.history(period="6mo")
    st.line_chart(hist["Close"])

    # --- Broker Ratings ---
    st.markdown("### 🧠 Broker Ratings")
    finnhub_key = st.secrets["finnhub"]["api_key"]
    ratings = get_broker_ratings(ticker, finnhub_key)
    sentiment = summarize_sentiment(ratings)

    if ratings:
        st.write(f"**Consensus Sentiment:** {sentiment}")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Strong Buy", ratings.get("strongBuy", "N/A"))
        col2.metric("Buy", ratings.get("buy", "N/A"))
        col3.metric("Hold", ratings.get("hold", "N/A"))
        col4.metric("Sell", ratings.get("sell", "N/A"))
        col5.metric("Strong Sell", ratings.get("strongSell", "N/A"))
    else:
        st.warning("No broker ratings available for this ticker.")

    # --- Earnings Section ---
    st.markdown("### 📅 Earnings Overview")
    if next_earnings:
        st.metric("Next Earnings Date", str(next_earnings.date()))
    else:
        st.warning("Next earnings date not available via yfinance.")

    surprises = get_earnings_surprises(ticker, finnhub_key)
    if surprises:
        df_eps = pd.DataFrame(surprises)[["period", "actual", "estimate"]]
        df_eps.columns = ["Period", "Actual EPS", "Estimated EPS"]
        st.dataframe(df_eps, use_container_width=True)
    else:
        st.warning("No historical earnings surprises available.")

    # --- News ---
    st.markdown("### 📰 Latest News")
    news = get_finnhub_news(ticker, finnhub_key)
    st.caption(f"Finnhub response type: `{type(news).__name__}`")

    if isinstance(news, list) and news:
        for item in news[:5]:
            st.markdown(f"- [{item['headline']}]({item['url']})")
    else:
        st.warning("No recent news from Finnhub. Showing fallback headlines from Yahoo Finance.")
        fallback_news = get_yahoo_news(ticker)
        if fallback_news:
            for item in fallback_news[:5]:
                st.markdown(f"- [{item['headline']}]({item['url']})")
        else:
            st.error("No fallback news available either.")

       