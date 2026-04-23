"""CFD Trading Signal System - Beautiful UI"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from analysis.indicators import IndicatorCalculator
    from analysis.sentiment import SentimentAnalyzer
    from analysis.earnings import EarningsChecker
    from agents.crew import CFDTradingCrew
    from utils.trade_card import TradeCardBuilder, TradeCardWriter
except ImportError:
    from trading_system.analysis.indicators import IndicatorCalculator
    from trading_system.analysis.sentiment import SentimentAnalyzer
    from trading_system.analysis.earnings import EarningsChecker
    from trading_system.agents.crew import CFDTradingCrew
    from trading_system.utils.trade_card import TradeCardBuilder, TradeCardWriter

import yaml
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / '.env')

st.set_page_config(page_title="🚀 Trading Signals", page_icon="📈", layout="wide")

# Industry & Stock Mapping
INDUSTRIES = {
    "⚡ Energy": ["XOM", "CVX", "COP", "MPC", "FANG"],
    "💻 Technology": ["NVDA", "MSFT", "META", "AAPL", "TSLA"],
    "🏦 Finance": ["JPM", "BAC", "GS", "WFC", "MS"],
    "🛍️ Consumer": ["AMZN", "MCD", "PG", "NKE", "SBUX"],
    "📦 Commodities": ["GLD", "USO", "SLV", "FCX", "DBA"]
}

# Beautiful Styling
st.markdown("""
<style>
    /* Dark theme with glow */
    .main { background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%); }
    
    /* Headers with glow effect */
    h1, h2, h3 { color: #00d4ff; text-shadow: 0 0 15px rgba(0,212,255,0.4); }
    
    /* Buttons */
    .stButton > button { 
        background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 8px;
        font-weight: bold;
        box-shadow: 0 0 20px rgba(0,212,255,0.3);
    }
    .stButton > button:hover { transform: scale(1.05); box-shadow: 0 0 30px rgba(0,212,255,0.6); }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #00ff41 0%, #00cc33 100%) !important;
        color: #000 !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

if 'last_results' not in st.session_state:
    st.session_state.last_results = None

@st.cache_resource
def init_system():
    with open(PROJECT_ROOT / 'config.yaml') as f:
        config = yaml.safe_load(f)
    return {
        'config': config,
        'indicator_calc': IndicatorCalculator(config),
        'sentiment_analyzer': SentimentAnalyzer(config),
        'earnings_checker': EarningsChecker(config),
        'trade_card_builder': TradeCardBuilder(config),
        'trade_card_writer': TradeCardWriter(config),
        'crew': CFDTradingCrew(config)
    }

def export_to_excel(cards):
    df = pd.DataFrame([
        {
            'Ticker': c.get('ticker', ''),
            'Signal': c.get('signal', ''),
            'Confidence': f"{c.get('confidence', 0):.0%}",
            'Entry': f"${c.get('entry_price', 0):.2f}",
            'Stop': f"${c.get('stop_loss', 0):.2f}",
            'TP1': f"${c.get('take_profit_1', 0):.2f}",
            'TP2': f"${c.get('take_profit_2', 0):.2f}",
            'Sentiment': f"{c.get('sentiment_score', 0):.2f}"
        } for c in cards
    ])
    buf = BytesIO()
    df.to_excel(buf, index=False, sheet_name='Signals')
    buf.seek(0)
    return buf.getvalue()

# ==================== MAIN UI ====================

st.title("🚀 CFD Trading Signal System")
st.markdown("**AI-powered trading signals** • Hybrid mode: CrewAI on BUY/SELL • Lightning fast ⚡")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🚀 Daily Scan", "📊 Results", "🔍 Analyze Stock", "ℹ️ About"])

with tab1:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader("⚡ Quick Scan")
    with col2:
        st.metric("Mode", "Hybrid", "✨")
    with col3:
        st.metric("Speed", "2-5 min", "🏃")
    
    st.markdown("**What happens:** Parallel download → Indicators → Sentiment → AI confirmation (BUY/SELL only)")
    
    if st.button("▶️ START SCAN", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        system = init_system()
        config = system['config']
        watchlist = config.get('watchlist', [])
        all_trade_cards = []
        
        status_text.text("📥 Downloading data...")
        daily_data = system['indicator_calc'].get_daily_data_parallel(watchlist, max_workers=5)
        
        all_indicators = {}
        for ticker in watchlist:
            try:
                data = daily_data.get(ticker)
                if data is not None:
                    ind = system['indicator_calc'].calculate_all_indicators_from_data(ticker, data)
                    if ind:
                        all_indicators[ticker] = ind
            except Exception as e:
                print(f"Error {ticker}: {e}")
        
        for idx, ticker in enumerate(watchlist):
            if ticker not in all_indicators:
                continue
            
            progress_bar.progress((idx + 1) / len(watchlist))
            ind = all_indicators[ticker]
            
            try:
                skip, date = system['earnings_checker'].check_earnings_within_threshold(ticker)
                if skip:
                    card = system['trade_card_builder'].build_trade_card(
                        ticker=ticker, signal="HOLD", current_price=ind['current_price'],
                        atr=ind['atr'], indicators_data=ind, confidence=0,
                        catalyst=f"Earnings {date}", sentiment_score=0, skip_reason="EARNINGS"
                    )
                    all_trade_cards.append(card)
                    continue
                
                rsi = ind.get('rsi', 50)
                macd = ind.get('macd_cross', '')
                
                if rsi < 35 and macd == 'bullish':
                    signal, conf = "BUY", 0.7
                elif rsi > 65 and macd == 'bearish':
                    signal, conf = "SELL", 0.7
                else:
                    signal, conf = "HOLD", 0.5
                
                sentiment = system['sentiment_analyzer'].calculate_sentiment_score(ticker)
                headlines = system['sentiment_analyzer'].get_top_headlines(ticker, limit=3)
                
                if signal in ["BUY", "SELL"]:
                    status_text.text(f"🧠 Confirming {ticker} with AI...")
                    card = system['crew'].run_signal_generation(
                        ticker=ticker, indicators_data=ind, sentiment_score=sentiment, top_headlines=headlines
                    )
                    if not card:
                        card = system['trade_card_builder'].build_trade_card(
                            ticker=ticker, signal=signal, current_price=ind['current_price'],
                            atr=ind['atr'], indicators_data=ind, confidence=conf,
                            catalyst=f"RSI={rsi} MACD={macd}", sentiment_score=sentiment, skip_reason="CREW_ERROR"
                        )
                else:
                    card = system['trade_card_builder'].build_trade_card(
                        ticker=ticker, signal="HOLD", current_price=ind['current_price'],
                        atr=ind['atr'], indicators_data=ind, confidence=conf,
                        catalyst=f"RSI={rsi} MACD={macd}", sentiment_score=sentiment, skip_reason="NO_SETUP"
                    )
                
                all_trade_cards.append(card)
            except Exception as e:
                st.warning(f"⚠️ Error {ticker}: {e}")
        
        status_text.text("✅ Scan complete!")
        if all_trade_cards:
            system['trade_card_writer'].write_trade_cards(all_trade_cards)
            st.session_state.last_results = all_trade_cards
            st.balloons()
            st.success(f"✨ Analyzed {len(all_trade_cards)} tickers successfully!")

with tab2:
    st.subheader("📊 Latest Results")
    if st.session_state.last_results:
        df = pd.DataFrame([
            {'Ticker': c.get('ticker', ''), 'Signal': c.get('signal', ''), 
             'Confidence': f"{c.get('confidence', 0):.0%}", 'Entry': f"${c.get('entry_price', 0):.2f}",
             'Stop': f"${c.get('stop_loss', 0):.2f}", 'TP1': f"${c.get('take_profit_1', 0):.2f}",
             'RSI': f"{c.get('rsi', 0):.0f}", 'Sentiment': f"{c.get('sentiment_score', 0):.2f}"}
            for c in st.session_state.last_results
        ])
        
        st.dataframe(df, use_container_width=True, height=500)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if st.button("📥 Export to Excel", use_container_width=True):
                st.download_button("⬇️ Download Excel", export_to_excel(st.session_state.last_results),
                                 f"signals_{datetime.now():%Y%m%d_%H%M%S}.xlsx", use_container_width=True)
        
        buys = len([c for c in st.session_state.last_results if c.get('signal') == 'BUY'])
        sells = len([c for c in st.session_state.last_results if c.get('signal') == 'SELL'])
        
        with col2:
            st.metric("🟢 BUY", buys)
        with col3:
            st.metric("🔴 SELL", sells)
    else:
        st.info("📊 No results yet. Run a scan to generate trading signals!")

with tab3:
    st.subheader("🔍 Analyze Individual Stock")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        industry = st.selectbox("📍 Select Industry", list(INDUSTRIES.keys()))
    
    with col2:
        stocks = INDUSTRIES[industry]
        selected_stock = st.selectbox("📈 Select Stock", stocks)
    
    with col3:
        analyze_btn = st.button("🔬 Analyze Now", use_container_width=True)
    
    if analyze_btn:
        system = init_system()
        status = st.empty()
        progress = st.progress(0)
        
        try:
            status.text(f"📥 Downloading {selected_stock} data...")
            progress.progress(20)
            
            # Get data for this stock
            data = system['indicator_calc'].get_daily_data_parallel([selected_stock], max_workers=1)
            if selected_stock in data and data[selected_stock] is not None:
                ind = system['indicator_calc'].calculate_all_indicators_from_data(selected_stock, data[selected_stock])
                progress.progress(50)
                
                # Get sentiment
                sentiment = system['sentiment_analyzer'].calculate_sentiment_score(selected_stock)
                headlines = system['sentiment_analyzer'].get_top_headlines(selected_stock, limit=5)
                progress.progress(70)
                
                # Get signal
                rsi = ind.get('rsi', 50)
                macd = ind.get('macd_cross', '')
                
                if rsi < 35 and macd == 'bullish':
                    signal, conf = "BUY", 0.7
                elif rsi > 65 and macd == 'bearish':
                    signal, conf = "SELL", 0.7
                else:
                    signal, conf = "HOLD", 0.5
                
                # Run AI confirmation for BUY/SELL
                if signal in ["BUY", "SELL"]:
                    status.text(f"🧠 Running CrewAI analysis for {selected_stock}...")
                    card = system['crew'].run_signal_generation(
                        ticker=selected_stock, indicators_data=ind, sentiment_score=sentiment, top_headlines=headlines
                    )
                else:
                    card = system['trade_card_builder'].build_trade_card(
                        ticker=selected_stock, signal=signal, current_price=ind['current_price'],
                        atr=ind['atr'], indicators_data=ind, confidence=conf,
                        catalyst=f"RSI={rsi} MACD={macd}", sentiment_score=sentiment, skip_reason="NO_SETUP"
                    )
                
                progress.progress(100)
                status.text("✅ Analysis complete!")
                
                # Display results
                st.success(f"✨ Analysis for {selected_stock}")
                
                col_sig, col_conf, col_price, col_sent = st.columns(4)
                with col_sig:
                    st.metric("Signal", card.get('signal', 'N/A'))
                with col_conf:
                    st.metric("Confidence", f"{card.get('confidence', 0):.0%}")
                with col_price:
                    st.metric("Current Price", f"${card.get('entry_price', 0):.2f}")
                with col_sent:
                    st.metric("Sentiment", f"{card.get('sentiment_score', 0):.2f}")
                
                # Display indicators
                st.subheader("📊 Technical Indicators")
                ind_col1, ind_col2, ind_col3, ind_col4 = st.columns(4)
                with ind_col1:
                    st.metric("RSI", f"{ind.get('rsi', 0):.1f}")
                with ind_col2:
                    st.metric("MACD", ind.get('macd_cross', 'N/A'))
                with ind_col3:
                    st.metric("ATR", f"${ind.get('atr', 0):.2f}")
                with ind_col4:
                    st.metric("SMA200", f"${ind.get('sma_200', 0):.2f}")
                
                # Headlines
                st.subheader("📰 Top Headlines")
                for i, headline in enumerate(headlines[:3], 1):
                    st.markdown(f"{i}. {headline}")
                
                # Trade card details
                st.subheader("💼 Trade Details")
                trade_col1, trade_col2, trade_col3 = st.columns(3)
                with trade_col1:
                    st.metric("Entry Price", f"${card.get('entry_price', 0):.2f}")
                with trade_col2:
                    st.metric("Stop Loss", f"${card.get('stop_loss', 0):.2f}")
                with trade_col3:
                    st.metric("Take Profit", f"${card.get('take_profit_1', 0):.2f}")
            else:
                st.error(f"Could not fetch data for {selected_stock}")
        except Exception as e:
            st.error(f"❌ Error analyzing {selected_stock}: {e}")

with tab4:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 System Overview
        **Smart Hybrid Architecture:**
        - 📥 Parallel data download (ThreadPoolExecutor)
        - 📊 Real-time technical indicators (RSI, MACD, ATR)
        - 📰 Sentiment analysis with 30-min cache
        - 🧠 CrewAI confirmation on strong signals only
        - 📁 Excel export for analysis
        
        ### ⚡ Performance
        - HOLD-only scans: **2-3 minutes**
        - BUY/SELL scans: **4-7 minutes** (includes AI)
        - Data caching: **30 minutes** (sentiment)
        """)
    
    with col2:
        st.markdown("""
        ### 📈 Technical Indicators
        **RSI (Relative Strength Index)**
        - Below 35 → Oversold (potential BUY)
        - Above 65 → Overbought (potential SELL)
        
        **MACD (Moving Average Convergence)**
        - Bullish cross → Uptrend confirmation
        - Bearish cross → Downtrend confirmation
        
        **AI Confirmation**
        - CrewAI analyzes BUY/SELL candidates
        - Uses: Price action, fundamentals, sentiment
        - HOLD signals skip AI (saves time)
        """)
    
    st.divider()
    st.markdown("**Made with ❤️ using Streamlit + CrewAI + yfinance**")

with tab4:
    col1, col2 = st.columns(2)
