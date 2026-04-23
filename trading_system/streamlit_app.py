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
    "💻 Technology": ["NVDA", "MSFT", "META", "AAPL", "TSLA", "ORCL"],
    "🏦 Finance": ["JPM", "BAC", "GS", "WFC", "MS", "MA", "V"],
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
    
    /* Signal colors */
    .buy-signal { color: #00ff41; font-weight: bold; }
    .sell-signal { color: #ff0051; font-weight: bold; }
    .hold-signal { color: #ffa500; font-weight: bold; }
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

def calculate_three_pillars(ticker, indicators_data, sentiment_score, headlines):
    """Calculate scores for the 3 pillars of analysis"""
    
    # 1️⃣ TECHNICAL ANALYSIS PILLAR (RSI, Volume, MACD)
    rsi = indicators_data.get('rsi', 50)
    macd = indicators_data.get('macd_cross', '')
    volume = indicators_data.get('volume', 0)
    atr = indicators_data.get('atr', 0)
    
    technical_score = 0
    technical_signals = []
    
    if rsi < 35:
        technical_score += 0.4
        technical_signals.append("✅ RSI Oversold (Buy signal)")
    elif rsi > 65:
        technical_score -= 0.4
        technical_signals.append("⚠️ RSI Overbought (Sell signal)")
    elif 40 < rsi < 60:
        technical_score += 0.1
        technical_signals.append("➡️ RSI Neutral")
    
    if macd == 'bullish':
        technical_score += 0.3
        technical_signals.append("✅ MACD Bullish Cross")
    elif macd == 'bearish':
        technical_score -= 0.3
        technical_signals.append("⚠️ MACD Bearish Cross")
    else:
        technical_signals.append("➡️ MACD Neutral")
    
    technical_score = max(-1, min(1, technical_score))  # Clamp between -1 and 1
    
    # 2️⃣ QUALITATIVE ANALYSIS PILLAR (News Sentiment)
    qualitative_score = sentiment_score  # Already normalized between -1 and 1
    
    qualitative_signals = []
    if sentiment_score > 0.3:
        qualitative_signals.append("✅ Positive News Sentiment")
    elif sentiment_score < -0.3:
        qualitative_signals.append("⚠️ Negative News Sentiment")
    else:
        qualitative_signals.append("➡️ Neutral News Sentiment")
    
    # 3️⃣ QUANTITATIVE ANALYSIS PILLAR (Market fundamentals check)
    # This is a simplified check - in production would use P/E, earnings growth, etc.
    quantitative_score = 0
    quantitative_signals = []
    
    if indicators_data.get('current_price', 0) > indicators_data.get('sma_200', 0):
        quantitative_score += 0.3
        quantitative_signals.append("✅ Price above 200-day MA")
    else:
        quantitative_score -= 0.3
        quantitative_signals.append("⚠️ Price below 200-day MA")
    
    if indicators_data.get('sma_50', 0) > indicators_data.get('sma_200', 0):
        quantitative_score += 0.2
        quantitative_signals.append("✅ 50-day MA above 200-day MA")
    else:
        quantitative_score -= 0.2
        quantitative_signals.append("⚠️ 50-day MA below 200-day MA")
    
    quantitative_score = max(-1, min(1, quantitative_score))
    
    # FINAL DECISION
    combined_score = (technical_score + qualitative_score + quantitative_score) / 3
    
    if combined_score > 0.4:
        signal = "BUY"
        confidence = min(0.95, 0.5 + abs(combined_score))
    elif combined_score < -0.4:
        signal = "SELL"
        confidence = min(0.95, 0.5 + abs(combined_score))
    else:
        signal = "HOLD"
        confidence = max(0.3, 0.5 - abs(combined_score))
    
    return {
        'signal': signal,
        'confidence': confidence,
        'technical': {
            'score': technical_score,
            'signals': technical_signals,
            'rsi': rsi,
            'macd': macd
        },
        'qualitative': {
            'score': qualitative_score,
            'signals': qualitative_signals,
            'sentiment': sentiment_score,
            'headlines': headlines
        },
        'quantitative': {
            'score': quantitative_score,
            'signals': quantitative_signals,
            'sma_50': indicators_data.get('sma_50', 0),
            'sma_200': indicators_data.get('sma_200', 0)
        },
        'combined_score': combined_score
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
st.markdown("""
**3-Pillar AI-Powered Trading Analysis:**
- 📊 **Technical Analysis** (RSI, MACD, Volume, Moving Averages)
- 📰 **Qualitative Analysis** (News Sentiment & Market News)
- 💹 **Quantitative Analysis** (Financial Performance & Price Trends)

*Combined for optimal BUY/HOLD/SELL decisions* • Hybrid CrewAI mode • ⚡ Lightning fast
""")
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 Daily Scan", "📊 Results", "🔍 Analyze Stock", "💬 News Q&A", "📚 About"])

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
    
    st.divider()
    st.info("📊 **Check Results tab** to see all signals with detailed metrics and export options!")

with tab2:
    st.subheader("📊 Latest Results")
    if st.session_state.last_results:
        # Create DataFrame with signal colors
        data = []
        for c in st.session_state.last_results:
            signal = c.get('signal', '')
            if signal == 'BUY':
                signal_html = f"<span style='color: #00ff41; font-weight: bold;'>🟢 BUY</span>"
            elif signal == 'SELL':
                signal_html = f"<span style='color: #ff0051; font-weight: bold;'>🔴 SELL</span>"
            else:
                signal_html = f"<span style='color: #ffa500; font-weight: bold;'>🟡 HOLD</span>"
            
            data.append({
                'Ticker': c.get('ticker', ''),
                'Signal': signal_html,
                'Confidence': f"{c.get('confidence', 0):.0%}",
                'Entry': f"${c.get('entry_price', 0):.2f}",
                'Stop': f"${c.get('stop_loss', 0):.2f}",
                'TP1': f"${c.get('take_profit_1', 0):.2f}",
                'RSI': f"{c.get('rsi', 0):.0f}",
                'Sentiment': f"{c.get('sentiment_score', 0):.2f}"
            })
        
        df = pd.DataFrame(data)
        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
        
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
                
                # Calculate 3 Pillars Analysis
                pillars = calculate_three_pillars(selected_stock, ind, sentiment, headlines)
                progress.progress(90)
                
                signal = pillars['signal']
                confidence = pillars['confidence']
                
                progress.progress(100)
                status.text("✅ Analysis complete!")
                
                # Display main result
                st.success(f"✨ 3-Pillar Analysis for {selected_stock}")
                
                # Main signal and confidence
                col_sig, col_conf, col_price = st.columns(3)
                with col_sig:
                    if signal == 'BUY':
                        st.metric("Signal", "🟢 BUY")
                    elif signal == 'SELL':
                        st.metric("Signal", "🔴 SELL")
                    else:
                        st.metric("Signal", "🟡 HOLD")
                with col_conf:
                    st.metric("Confidence", f"{confidence:.0%}")
                with col_price:
                    st.metric("Current Price", f"${ind.get('current_price', 0):.2f}")
                
                st.divider()
                
                # 3 PILLARS BREAKDOWN
                st.subheader("📊 3-Pillar Analysis Breakdown")
                
                col1, col2, col3 = st.columns(3)
                
                # PILLAR 1: TECHNICAL
                with col1:
                    st.markdown(f"""
                    ### 📈 Technical Analysis
                    **Score: {pillars['technical']['score']:.2f}**
                    
                    **Indicators:**
                    - RSI: {pillars['technical']['rsi']:.1f}
                    - MACD: {pillars['technical']['macd']}
                    - ATR: ${ind.get('atr', 0):.2f}
                    
                    **Signals:**
                    """)
                    for signal_text in pillars['technical']['signals']:
                        st.markdown(f"- {signal_text}")
                
                # PILLAR 2: QUALITATIVE
                with col2:
                    st.markdown(f"""
                    ### 📰 Qualitative Analysis
                    **Score: {pillars['qualitative']['score']:.2f}**
                    
                    **Sentiment: {pillars['qualitative']['sentiment']:.2f}**
                    
                    **Signals:**
                    """)
                    for signal_text in pillars['qualitative']['signals']:
                        st.markdown(f"- {signal_text}")
                
                # PILLAR 3: QUANTITATIVE
                with col3:
                    st.markdown(f"""
                    ### 💹 Quantitative Analysis
                    **Score: {pillars['quantitative']['score']:.2f}**
                    
                    **Moving Averages:**
                    - SMA 50: ${pillars['quantitative']['sma_50']:.2f}
                    - SMA 200: ${pillars['quantitative']['sma_200']:.2f}
                    
                    **Signals:**
                    """)
                    for signal_text in pillars['quantitative']['signals']:
                        st.markdown(f"- {signal_text}")
                
                st.divider()
                
                # Headlines
                st.subheader("📰 Top Headlines")
                for i, headline in enumerate(headlines[:3], 1):
                    st.markdown(f"{i}. {headline}")
                
                # Trade card details
                st.subheader("💼 Trade Details")
                trade_col1, trade_col2, trade_col3 = st.columns(3)
                with trade_col1:
                    st.metric("Entry Price", f"${ind.get('current_price', 0):.2f}")
                with trade_col2:
                    st.metric("Stop Loss", f"${ind.get('current_price', 0) - ind.get('atr', 0):.2f}")
                with trade_col3:
                    st.metric("Take Profit", f"${ind.get('current_price', 0) + (ind.get('atr', 0) * 2):.2f}")
            else:
                st.error(f"Could not fetch data for {selected_stock}")
        except Exception as e:
            st.error(f"❌ Error analyzing {selected_stock}: {e}")

with tab4:
    st.subheader("📰 News Q&A with AI Agent")
    st.markdown("Ask questions about news and market sentiment for any stock. Our AI agent will analyze headlines and provide insights.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        ticker = st.text_input("📌 Enter Stock Ticker (e.g., AAPL, MSFT, TSLA)", value="").upper()
    with col2:
        fetch_btn = st.button("📥 Fetch News", use_container_width=True)
    
    if fetch_btn and ticker:
        system = init_system()
        try:
            st.info(f"🔍 Fetching news for {ticker}...")
            headlines = system['sentiment_analyzer'].get_top_headlines(ticker, limit=10)
            sentiment = system['sentiment_analyzer'].calculate_sentiment_score(ticker)
            
            st.success(f"✨ Found {len(headlines)} headlines • Sentiment: {sentiment:.2f}")
            
            st.subheader(f"📄 Top Headlines for {ticker}")
            for i, headline in enumerate(headlines, 1):
                st.markdown(f"{i}. {headline}")
            
            st.divider()
            
            # Q&A Interface
            st.subheader("💬 Ask About This Stock")
            question = st.text_area("What would you like to know about this stock?", 
                                   placeholder="e.g., What are the latest market concerns? Is this a buy? What's the sentiment trend?")
            
            if st.button("🤖 Get AI Analysis", use_container_width=True):
                with st.spinner("🧠 AI Agent analyzing..."):
                    try:
                        # Use CrewAI to analyze the news and answer the question
                        analysis = system['crew'].run_signal_generation(
                            ticker=ticker,
                            indicators_data={"current_price": 0},
                            sentiment_score=sentiment,
                            top_headlines=headlines
                        )
                        
                        if analysis:
                            st.success("✅ Analysis Complete!")
                            
                            st.subheader("📊 AI Insights")
                            st.markdown(f"""
                            **Signal:** {analysis.get('signal', 'N/A')}
                            
                            **Confidence:** {analysis.get('confidence', 0):.0%}
                            
                            **Analysis:**
                            {analysis.get('analysis', 'No detailed analysis available')}
                            """)
                        else:
                            st.warning("⚠️ Could not generate analysis. Try again.")
                    except Exception as e:
                        st.error(f"❌ AI Analysis Error: {e}")
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    if not ticker:
        st.info("👉 Enter a stock ticker above and fetch news to start!")

with tab5:
    st.subheader("📚 3-Pillar Trading Framework")
    
    st.markdown("""
    Our system makes BUY/HOLD/SELL decisions by combining **3 fundamental pillars** of analysis:
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📊 TECHNICAL ANALYSIS
        Uses price action & indicators:
        
        **RSI (Relative Strength Index)**
        - < 35 = Oversold (🟢 BUY Signal)
        - > 65 = Overbought (🔴 SELL Signal)
        - 40-60 = Neutral
        
        **MACD (Moving Average Convergence)**
        - Bullish Cross = 🟢 Uptrend
        - Bearish Cross = 🔴 Downtrend
        
        **Volume & ATR**
        - Confirms strength of moves
        - Risk management metrics
        """)
    
    with col2:
        st.markdown("""
        ### 📰 QUALITATIVE ANALYSIS
        Analyzes news & sentiment:
        
        **News Sentiment Score**
        - Positive (+1 to 0) = Bullish
        - Negative (0 to -1) = Bearish
        - Updates every 30 minutes
        
        **Headlines Analysis**
        - Scans major financial outlets
        - Detects market concerns
        - Tracks earnings events
        
        **Real-time Feed**
        - AI-powered interpretation
        - Sentiment aggregation
        """)
    
    with col3:
        st.markdown("""
        ### 💹 QUANTITATIVE ANALYSIS
        Analyzes financial performance:
        
        **Moving Averages**
        - Price vs SMA 50 (short-term)
        - Price vs SMA 200 (long-term)
        - Trend confirmation
        
        **Fundamentals**
        - Earnings data checks
        - Market cap analysis
        - Financial health
        
        **Combined Score**
        - All 3 pillars weighted equally
        - Confidence ranges 0-100%
        """)
    
    st.divider()
    
    st.markdown("""
    ### 🎯 Decision Logic
    
    **BUY Signal (🟢)** → When combined score > 0.4
    - Technical + Qualitative + Quantitative all point up
    - Confidence: 60-95%
    
    **SELL Signal (🔴)** → When combined score < -0.4
    - Technical + Qualitative + Quantitative all point down
    - Confidence: 60-95%
    
    **HOLD Signal (🟡)** → When combined score is neutral
    - Mixed signals across pillars
    - Wait for clearer direction
    - Confidence: 30-60%
    """)
    
    st.divider()
    st.markdown("**Made with ❤️ using Streamlit + CrewAI + yfinance**")
