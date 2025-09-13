import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np

st.set_page_config(page_title="Advanced Real-Time Stock Dashboard", layout="wide")
st.title("📈 Real-Time Stock Dashboard with Insights")

# --- Sidebar Inputs ---
ticker = st.sidebar.text_input("Ticker Symbol", "MSFT")
interval = st.sidebar.selectbox("Data Interval", ["1m", "5m", "15m"])
refresh_seconds = st.sidebar.slider("Update Every (seconds)", 10, 60, 15)
target_price = st.sidebar.number_input("Set Price Alert", value=0.0)

# --- Auto-refresh ---
st_autorefresh(interval=refresh_seconds * 1000, key="ticker_refresh")

# --- Sidebar Insights Panel ---
st.sidebar.header("📊 Key Insights")
price_metric = st.sidebar.empty()
change_metric = st.sidebar.empty()
volume_metric = st.sidebar.empty()
high_metric = st.sidebar.empty()
low_metric = st.sidebar.empty()
trend_metric = st.sidebar.empty()

# --- Placeholders ---
chart_placeholder = st.empty()
summary_placeholder = st.empty()
ticker_placeholder = st.empty()
pricing_tab, fundamental_tab, news_tab = st.tabs(
    ["💰 Pricing Data", "📊 Fundamentals", "📰 Top News"]
)

# --- Fetch Data Function ---
def fetch_data(ticker, interval):
    df = yf.download(ticker, period="1d", interval=interval)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df["% Change"] = df["Close"].pct_change() * 100
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    return df

# --- News Sentiment (simple) ---
def sentiment_emoji(title):
    positive_keywords = ["surge", "rise", "gain", "beat", "up", "profit"]
    negative_keywords = ["fall", "drop", "loss", "decline", "down", "miss"]
    title_lower = title.lower()
    if any(word in title_lower for word in positive_keywords):
        return "🟢"
    elif any(word in title_lower for word in negative_keywords):
        return "🔴"
    else:
        return "⚪"

# --- Main Logic ---
try:
    data = fetch_data(ticker, interval)
    if data.empty:
        st.warning("No data found for this ticker.")
    else:
        # --- Simulate small live price changes ---
        last_close = data["Close"].iloc[-1]
        simulated_close = last_close * (1 + np.random.uniform(-0.001, 0.001))
        data["Close"].iloc[-1] = simulated_close
        data["% Change"].iloc[-1] = (simulated_close - data["Close"].iloc[0]) / data["Close"].iloc[0] * 100

        # --- Update Sidebar Metrics ---
        price_metric.metric("Current Price", f"${data['Close'].iloc[-1]:.2f}")
        change_metric.metric("Day Change", f"{data['% Change'].iloc[-1]:.2f}%")
        volume_metric.metric("Volume", f"{data['Volume'].iloc[-1]:,}")
        high_metric.metric("52 Week High", f"${yf.Ticker(ticker).info.get('fiftyTwoWeekHigh')}")
        low_metric.metric("52 Week Low", f"${yf.Ticker(ticker).info.get('fiftyTwoWeekLow')}")
        
        trend = "Uptrend 🟢" if data["MA20"].iloc[-1] > data["MA50"].iloc[-1] else "Downtrend 🔴"
        trend_metric.metric("Short-Term Trend", trend)

        # --- Safe News Fetch ---
        news_data_raw = yf.Ticker(ticker).news
        news_data = []
        if news_data_raw:
            for article in news_data_raw:
                if 'title' in article and 'link' in article:
                    news_data.append(article)

        # --- Live Scrolling News ---
        if news_data:
            latest_news = [f"{sentiment_emoji(article['title'])} {article['title']}" for article in news_data[:5]]
            news_text = " | ".join(latest_news)
            ticker_placeholder.markdown(f"""
            <div style="white-space: nowrap; overflow: hidden;">
                <marquee>{news_text}</marquee>
            </div>
            """, unsafe_allow_html=True)
        else:
            ticker_placeholder.write("No news found.")

        # --- Pricing Data Tab ---
        with pricing_tab:
            st.subheader("Candlestick Chart with MA20 & MA50")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['Open'], high=data['High'],
                low=data['Low'], close=data['Close'],
                name="Candlestick"
            ))
            fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], line=dict(color='blue', width=1), name="MA20"))
            fig.add_trace(go.Scatter(x=data.index, y=data["MA50"], line=dict(color='orange', width=1), name="MA50"))

            # Volume bars
            fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name="Volume", yaxis='y2', marker_color='lightgray'))

            # Layout
            fig.update_layout(
                title=f"{ticker} Candlestick Chart",
                xaxis_title="Time",
                yaxis_title="Price",
                yaxis=dict(title='Price'),
                yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False, position=1.0),
                xaxis_rangeslider_visible=False,
                height=600
            )
            chart_placeholder.plotly_chart(fig, use_container_width=True, key=f"candlestick_{ticker}_{interval}")

            # Summary Statistics
            summary_placeholder.subheader("Summary Statistics")
            summary_placeholder.write(data.describe().round(2))

            # Price Alert
            if target_price > 0 and data["Close"].iloc[-1] >= target_price:
                st.success(f"🚨 {ticker} crossed your target price of {target_price}!")

        # --- Fundamentals Tab ---
        with fundamental_tab:
            st.header(f"{ticker} Fundamentals")
            info = yf.Ticker(ticker).info
            fundamentals = {
                "Previous Close": info.get("previousClose"),
                "Open": info.get("open"),
                "Day Low": info.get("dayLow"),
                "Day High": info.get("dayHigh"),
                "Market Cap": info.get("marketCap"),
                "PE Ratio": info.get("trailingPE"),
                "EPS": info.get("trailingEps"),
                "Dividend Yield": info.get("dividendYield"),
                "Sector": info.get("sector"),
                "Industry": info.get("industry")
            }
            st.json(fundamentals)

        # --- News Tab ---
        with news_tab:
            st.header(f"{ticker} Latest News")
            if news_data:
                for article in news_data[:10]:
                    st.markdown(f"{sentiment_emoji(article['title'])} **[{article['title']}]({article['link']})**")
                    publisher = article.get('publisher', 'Unknown')
                    date = article.get('providerPublishTime')
                    if date:
                        date = pd.to_datetime(date, unit='s')
                    st.write(f"Publisher: {publisher}, Date: {date}")
                    st.write("---")
            else:
                st.write("No recent news found.")

except Exception as e:
    st.error(f"Error fetching data: {e}")

