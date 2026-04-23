"""CFD Trading Signal System - Minimal Version"""
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

st.set_page_config(page_title="Trading Signals", page_icon="📈", layout="wide")

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

st.header("🚀 Trading Signals")
tab1, tab2, tab3 = st.tabs(["🚀 Scan", "📊 Results", "❓ About"])

with tab1:
    st.markdown("**Quick Scan** (parallel data, AI only on BUY/SELL)")
    
    if st.button("▶️ Start Scan"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        system = init_system()
        config = system['config']
        watchlist = config.get('watchlist', [])
        all_trade_cards = []
        
        # Download all data in parallel
        status_text.text("📥 Downloading...")
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
        
        # Process tickers
        for idx, ticker in enumerate(watchlist):
            if ticker not in all_indicators:
                continue
            
            progress_bar.progress((idx + 1) / len(watchlist))
            ind = all_indicators[ticker]
            
            try:
                # Skip earnings
                skip, date = system['earnings_checker'].check_earnings_within_threshold(ticker)
                if skip:
                    card = system['trade_card_builder'].build_trade_card(
                        ticker=ticker, signal="HOLD", current_price=ind['current_price'],
                        atr=ind['atr'], indicators_data=ind, confidence=0,
                        catalyst=f"Earnings {date}", sentiment_score=0, skip_reason="EARNINGS"
                    )
                    all_trade_cards.append(card)
                    continue
                
                # Fast signal
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
                
                # Only use AI for BUY/SELL
                if signal in ["BUY", "SELL"]:
                    status_text.text(f"🧠 AI → {ticker}")
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
                st.warning(f"Error {ticker}: {e}")
        
        status_text.text("✅ Done!")
        if all_trade_cards:
            system['trade_card_writer'].write_trade_cards(all_trade_cards)
            st.session_state.last_results = all_trade_cards

with tab2:
    st.subheader("📊 Results")
    if st.session_state.last_results:
        df = pd.DataFrame([
            {'Ticker': c.get('ticker', ''), 'Signal': c.get('signal', ''), 
             'Confidence': f"{c.get('confidence', 0):.0%}", 'Entry': f"${c.get('entry_price', 0):.2f}",
             'Stop': f"${c.get('stop_loss', 0):.2f}", 'RSI': f"{c.get('rsi', 0):.0f}",
             'MACD': c.get('macd_cross', ''), 'Sentiment': f"{c.get('sentiment_score', 0):.2f}"}
            for c in st.session_state.last_results
        ])
        st.dataframe(df, use_container_width=True)
        if st.button("📥 Export Excel"):
            st.download_button("Download", export_to_excel(st.session_state.last_results),
                             f"signals_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
    else:
        st.info("No results yet")

with tab3:
    st.markdown("## Trading Signal System\n- **RSI**: Oversold/overbought\n- **MACD**: Momentum\n- **Sentiment**: News analysis\n- **AI**: Only confirms BUY/SELL\n\n**Speed**: 2-5 min (AI only when needed)")
