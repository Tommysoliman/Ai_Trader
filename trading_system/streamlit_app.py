"""
Streamlit Dashboard for CFD Trading Signal System
Web UI to view and trigger trading signal generation
"""

import streamlit as st
import pandas as pd
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import pytz
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.lib import colors
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

# Add project to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.indicators import IndicatorCalculator
from analysis.sentiment import SentimentAnalyzer
from analysis.earnings import EarningsChecker
from agents.crew import CFDTradingCrew
from utils.trade_card import TradeCardBuilder, TradeCardWriter
import yaml
from dotenv import load_dotenv

# Load environment
load_dotenv(PROJECT_ROOT / '.env')

# Page config
st.set_page_config(
    page_title="CFD Trading Signal System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .buy-signal {
        background-color: #d4edda;
        padding: 15px;
        border-left: 4px solid #28a745;
        border-radius: 5px;
        margin: 10px 0;
    }
    .sell-signal {
        background-color: #f8d7da;
        padding: 15px;
        border-left: 4px solid #dc3545;
        border-radius: 5px;
        margin: 10px 0;
    }
    .hold-signal {
        background-color: #fff3cd;
        padding: 15px;
        border-left: 4px solid #ffc107;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'system_initialized' not in st.session_state:
    st.session_state.system_initialized = False
    st.session_state.last_results = None
    st.session_state.running = False

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    
if 'chat_ticker_context' not in st.session_state:
    st.session_state.chat_ticker_context = None

# Load configuration
@st.cache_resource
def load_config():
    config_path = PROJECT_ROOT / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

@st.cache_resource
def init_system():
    config = load_config()
    return {
        'config': config,
        'indicator_calc': IndicatorCalculator(config),
        'sentiment_analyzer': SentimentAnalyzer(config),
        'earnings_checker': EarningsChecker(config),
        'trade_card_builder': TradeCardBuilder(config),
        'trade_card_writer': TradeCardWriter(config),
        'crew': CFDTradingCrew(config)
    }

# Helper function: Export trade cards to Excel
def export_to_excel(trade_cards_data):
    """Convert trade cards to Excel file"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Trade Signals"
    
    # Headers
    headers = [
        "Ticker", "Signal", "Confidence", "Entry Price", "Stop Loss", 
        "TP1", "TP2", "Leverage", "Catalyst", "Sentiment Score", "RSI", 
        "MACD Cross", "Above 200 SMA"
    ]
    
    ws.append(headers)
    
    # Style header row
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Add data rows
    for card in trade_cards_data:
        signal = card.get('signal', '')
        row = [
            card.get('ticker', ''),
            signal,
            card.get('confidence', 0),
            card.get('entry_price', 0),
            card.get('stop_loss', 0),
            card.get('take_profit_1', 0),
            card.get('take_profit_2', 0),
            f"{card.get('leverage_recommended', 0)}:1",
            card.get('catalyst', '')[:50],
            card.get('sentiment_score', 0),
            card.get('rsi', 0),
            card.get('macd_cross', 'none'),
            "Yes" if card.get('above_200sma', False) else "No"
        ]
        ws.append(row)
        
        # Color code by signal type
        if signal == 'BUY':
            fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        elif signal == 'SELL':
            fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        else:
            fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        
        for cell in ws[ws.max_row]:
            cell.fill = fill
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 10
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 12
    ws.column_dimensions['I'].width = 20
    ws.column_dimensions['J'].width = 12
    ws.column_dimensions['K'].width = 10
    ws.column_dimensions['L'].width = 12
    ws.column_dimensions['M'].width = 14
    
    # Save to BytesIO
    excel_buffer = BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()

# Helper function: Get news agent insights
def get_news_agent_answer(question: str, system) -> str:
    """Chat with News Agent to get headlines and sentiment analysis"""
    try:
        from crewai import Task, Crew, Process
        from agents.agents import CFDTradingAgents
        
        # Extract ticker from question
        ticker = None
        words = question.upper().split()
        for word in words:
            # Look for 1-5 letter tickers
            if 1 <= len(word) <= 5 and word.isalpha():
                ticker = word
                break
        
        if not ticker:
            return "📰 Please mention a specific ticker in your question (e.g., 'What's the latest news on AAPL?')"
        
        # Get sentiment and headlines
        try:
            sentiment_score = system['sentiment_analyzer'].calculate_sentiment_score(ticker)
            headlines = system['sentiment_analyzer'].get_top_headlines(ticker, limit=5)
        except:
            sentiment_score = 0.0
            headlines = []
        
        # Format context for news agent
        headlines_text = "\n".join([f"- {h.get('title', 'No title')}" for h in headlines]) if headlines else "No recent headlines found"
        
        context = f"""You are a financial news analyst specializing in market sentiment analysis. Current news context for {ticker}:

SENTIMENT SCORE: {sentiment_score:.2f}
Interpretation: {'Bullish 📈' if sentiment_score > 0.2 else 'Bearish 📉' if sentiment_score < -0.2 else 'Neutral/Mixed 📊'}

RECENT HEADLINES (Last 24H):
{headlines_text}

USER QUESTION: {question}

Provide a brief but insightful analysis of the news and sentiment for {ticker}. Address what the headlines suggest about future price movement."""
        
        agents_factory = CFDTradingAgents()
        news_agent = agents_factory.news_researcher()
        
        task = Task(
            description=context,
            agent=news_agent,
            expected_output="Concise news analysis with sentiment interpretation"
        )
        
        crew = Crew(
            agents=[news_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        answer = str(result).strip() if result else f"📰 No recent news analysis available for {ticker}"
        
        # Limit response length
        if len(answer) > 500:
            answer = answer[:500] + "...\n\n[Response truncated]"
        
        return answer
    
    except Exception as e:
        import traceback
        print(f"News agent error: {traceback.format_exc()}")
        return f"📰 News agent unavailable. Error: {type(e).__name__}"

# Helper function: Get agent answer about trade cards
def get_agent_answer(question: str, trade_cards_data: list, system, agent_type: str = "analyst") -> str:
    """Use agents to answer questions about trade cards
    
    Args:
        question: User's question
        trade_cards_data: List of trade card dictionaries
        system: System object with initialized components
        agent_type: "analyst" for portfolio manager, "news" for news agent
    """
    try:
        if agent_type == "news":
            return get_news_agent_answer(question, system)
        
        # Format trade card data for context
        buy_cards = [c for c in trade_cards_data if c.get('signal') == 'BUY']
        sell_cards = [c for c in trade_cards_data if c.get('signal') == 'SELL']
        hold_cards = [c for c in trade_cards_data if c.get('signal') == 'HOLD']
        
        # Build concise context for analyst
        buy_summary = [f"{c['ticker']}: {c.get('confidence', 0)}% confidence, Catalyst: {c.get('catalyst', 'N/A')[:30]}" for c in buy_cards[:3]]
        sell_summary = [f"{c['ticker']}: {c.get('confidence', 0)}% confidence, Catalyst: {c.get('catalyst', 'N/A')[:30]}" for c in sell_cards[:3]]
        
        context = f"""You are a trading analyst expert. Here's the current market analysis summary:

TRADING ENVIRONMENT:
- Total Signals: {len(trade_cards_data)}
- BUY Signals: {len(buy_cards)} | SELL Signals: {len(sell_cards)} | HOLD Signals: {len(hold_cards)}

TOP BUY OPPORTUNITIES:
{chr(10).join(buy_summary) if buy_summary else 'None currently'}

TOP SELL OPPORTUNITIES:
{chr(10).join(sell_summary) if sell_summary else 'None currently'}

USER QUESTION: {question}

Provide a concise, actionable trading analysis answer. Be specific and reference tickers when relevant."""
        
        # Try using portfolio manager agent for trade analysis
        from crewai import Task, Crew, Process
        from agents.agents import CFDTradingAgents
        
        agents_factory = CFDTradingAgents()
        portfolio_agent = agents_factory.portfolio_manager()
        
        task = Task(
            description=context,
            agent=portfolio_agent,
            expected_output="Clear, specific trading analysis answer addressing the user's question"
        )
        
        crew = Crew(
            agents=[portfolio_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        answer = str(result).strip() if result else "I couldn't generate an analysis. Please try again."
        
        # Limit response length for UI
        if len(answer) > 500:
            answer = answer[:500] + "...\n\n[Response truncated for display]"
        
        return answer
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Agent error: {error_detail}")
        return f"⚠️ Agent temporarily unavailable. Please try again. (Error: {type(e).__name__})"

# Header
st.title("🤖 CFD Trading Signal System")
st.markdown("*Real-time trading signal generation using AI agents*")
st.divider()

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    config = load_config()
    watchlist = config.get('watchlist', [])
    
    st.markdown("### Watchlist")
    st.caption(f"Total Tickers: {len(watchlist)}")
    
    with st.expander("View Watchlist"):
        for i, ticker in enumerate(watchlist, 1):
            st.text(f"{i}. {ticker}")
    
    st.divider()
    
    st.markdown("### Thresholds")
    rsi_bullish = config.get('indicators', {}).get('rsi_bullish_threshold', 45)
    rsi_bearish = config.get('indicators', {}).get('rsi_bearish_threshold', 58)
    sentiment_bullish = config.get('sentiment', {}).get('bullish_threshold', 0.2)
    sentiment_bearish = config.get('sentiment', {}).get('bearish_threshold', -0.2)
    
    st.metric("RSI Bullish (<)", rsi_bullish)
    st.metric("RSI Bearish (>)", rsi_bearish)
    st.metric("Sentiment Bullish (>)", sentiment_bullish)
    st.metric("Sentiment Bearish (<)", sentiment_bearish)
    
    st.divider()
    
    st.markdown("### MiFID II Leverage Caps")
    leverage = config.get('leverage', {})
    st.metric("Stocks", f"{leverage.get('stock_cfd_max', 5)}:1")
    st.metric("Commodities", f"{leverage.get('commodity_cfd_max', 10)}:1")
    st.metric("Crypto", f"{leverage.get('crypto_cdf_max', 2)}:1")

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Run Signals",
    "📊 View Results",
    "📁 Historical",
    "ℹ️ About"
])

# ==================== TAB 1: RUN SIGNALS ====================
with tab1:
    st.header("🚀 Trigger Signal Generation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Quick Scan")
        st.markdown("""
        Run a full daily scan on the watchlist:
        - Download OHLCV data
        - Calculate technical indicators
        - Fetch news & sentiment
        - Run CrewAI pipeline
        - Generate trade cards
        """)
        
        if st.button("▶️ Start Daily Scan", key="daily_scan", help="Run full signal generation"):
            st.session_state.running = True
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            system = init_system()
            config = system['config']
            watchlist = config.get('watchlist', [])
            
            all_trade_cards = []
            
            for idx, ticker in enumerate(watchlist):
                progress = (idx + 1) / len(watchlist)
                progress_bar.progress(progress)
                status_text.text(f"Processing {ticker}... ({idx + 1}/{len(watchlist)})")
                
                try:
                    # Get indicators
                    indicators_data = system['indicator_calc'].calculate_all_indicators(ticker)
                    
                    if not indicators_data:
                        continue
                    
                    # Check earnings
                    skip_earnings, earnings_date = system['earnings_checker'].check_earnings_within_threshold(ticker)
                    if skip_earnings:
                        trade_card = system['trade_card_builder'].build_trade_card(
                            ticker=ticker,
                            signal="HOLD",
                            current_price=indicators_data['current_price'],
                            atr=indicators_data['atr'],
                            indicators_data=indicators_data,
                            confidence=0,
                            catalyst=f"Earnings on {earnings_date}",
                            sentiment_score=0.0,
                            skip_reason="EARNINGS"
                        )
                        all_trade_cards.append(trade_card)
                        continue
                    
                    # Get sentiment
                    sentiment_score = system['sentiment_analyzer'].calculate_sentiment_score(ticker)
                    top_headlines = system['sentiment_analyzer'].get_top_headlines(ticker, limit=3)
                    
                    # Run crew
                    trade_card = system['crew'].run_signal_generation(
                        ticker=ticker,
                        indicators_data=indicators_data,
                        sentiment_score=sentiment_score,
                        top_headlines=top_headlines
                    )
                    
                    if trade_card:
                        all_trade_cards.append(trade_card)
                    else:
                        trade_card = system['trade_card_builder'].build_trade_card(
                            ticker=ticker,
                            signal="HOLD",
                            current_price=indicators_data['current_price'],
                            atr=indicators_data['atr'],
                            indicators_data=indicators_data,
                            confidence=0,
                            catalyst="Crew processing error",
                            sentiment_score=sentiment_score,
                            skip_reason="AGENT_ERROR"
                        )
                        all_trade_cards.append(trade_card)
                
                except Exception as e:
                    st.warning(f"Error processing {ticker}: {e}")
            
            progress_bar.progress(1.0)
            status_text.text("✅ Scan complete!")
            
            # Save results
            if all_trade_cards:
                system['trade_card_writer'].write_trade_cards(all_trade_cards)
                st.session_state.last_results = all_trade_cards
            
            st.session_state.running = False
    
    with col2:
        st.subheader("Single Ticker")
        st.markdown("Analyze a specific ticker")
        
        ticker_input = st.selectbox(
            "Select ticker:",
            config.get('watchlist', []),
            key="single_ticker"
        )
        
        if st.button("📊 Analyze", key="analyze_single"):
            system = init_system()
            
            status = st.status("Analyzing...")
            
            with status:
                st.write(f"📥 Fetching data for {ticker_input}...")
                indicators_data = system['indicator_calc'].calculate_all_indicators(ticker_input)
                
                if not indicators_data:
                    st.error("No data available for this ticker")
                else:
                    st.write(f"📰 Getting sentiment...")
                    sentiment_score = system['sentiment_analyzer'].calculate_sentiment_score(ticker_input)
                    top_headlines = system['sentiment_analyzer'].get_top_headlines(ticker_input, limit=3)
                    
                    st.write(f"🤖 Running AI analysis...")
                    trade_card = system['crew'].run_signal_generation(
                        ticker=ticker_input,
                        indicators_data=indicators_data,
                        sentiment_score=sentiment_score,
                        top_headlines=top_headlines
                    )
                    
                    if trade_card:
                        st.session_state.last_results = [trade_card]
            
            status.update(label="✅ Analysis complete!", state="complete")

# ==================== TAB 2: VIEW RESULTS ====================
with tab2:
    st.header("📊 Trade Card Results")
    
    if st.session_state.last_results:
        results = st.session_state.last_results
        
        # Create two columns: left for trade cards, right for chat
        col_main, col_chat = st.columns([2, 1.2], gap="medium")
        
        # ===== LEFT COLUMN: TRADE CARDS =====
        with col_main:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            buy_count = len([c for c in results if c['signal'] == 'BUY'])
            sell_count = len([c for c in results if c['signal'] == 'SELL'])
            hold_count = len([c for c in results if c['signal'] == 'HOLD'])
            avg_confidence = sum([c['confidence'] for c in results]) / len(results) if results else 0
            
            with col1:
                st.metric("🟢 BUY Signals", buy_count)
            with col2:
                st.metric("🔴 SELL Signals", sell_count)
            with col3:
                st.metric("🟡 HOLD Signals", hold_count)
            with col4:
                st.metric("📈 Avg Confidence", f"{avg_confidence:.0f}%")
            
            st.divider()
            
            # Trade cards display
            st.subheader("Trade Cards")
            
            # Filter options
            col1, col2, col3 = st.columns(3)
            with col1:
                signal_filter = st.multiselect(
                    "Filter by Signal:",
                    ["BUY", "SELL", "HOLD"],
                    default=["BUY", "SELL", "HOLD"],
                    key="signal_filter_tab2"
                )
            with col2:
                min_confidence = st.slider(
                    "Min Confidence:",
                    0, 100, 0,
                    key="confidence_slider_tab2"
                )
            with col3:
                sort_by = st.selectbox(
                    "Sort by:",
                    ["Confidence (High-Low)", "Ticker (A-Z)", "Signal"],
                    key="sort_by_tab2"
                )
            
            # Filter and sort with explicit logic
            if not signal_filter:
                # If no signals selected, show empty
                filtered_results = []
            else:
                filtered_results = [
                    c for c in results 
                    if c['signal'] in signal_filter and c['confidence'] >= min_confidence
                ]
            
            # Sort results
            if sort_by == "Confidence (High-Low)":
                filtered_results.sort(key=lambda x: x['confidence'], reverse=True)
            elif sort_by == "Ticker (A-Z)":
                filtered_results.sort(key=lambda x: x['ticker'])
            elif sort_by == "Signal":
                signal_order = {"BUY": 0, "SELL": 1, "HOLD": 2}
                filtered_results.sort(key=lambda x: signal_order.get(x['signal'], 3))
            
            # Show results info
            st.info(f"📊 Showing {len(filtered_results)} of {len(results)} trade cards")
            
            # Display cards
            for card in filtered_results:
                signal = card['signal']
                ticker = card['ticker']
                confidence = card['confidence']
                
                # Choose color based on signal
                if signal == 'BUY':
                    signal_class = "buy-signal"
                    signal_icon = "🟢"
                elif signal == 'SELL':
                    signal_class = "sell-signal"
                    signal_icon = "🔴"
                else:
                    signal_class = "hold-signal"
                    signal_icon = "🟡"
                
                with st.expander(f"{signal_icon} {ticker} - {signal} (Confidence: {confidence}%)"):
                    # Only show detailed trading info for BUY/SELL signals
                    if signal in ['BUY', 'SELL']:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Entry Strategy**")
                            entry_low = card.get('entry_zone_low')
                            entry_high = card.get('entry_zone_high')
                            entry_price = card.get('entry_price')
                            stop_loss = card.get('stop_loss')
                            
                            if entry_low is not None and entry_high is not None:
                                st.write(f"Entry Zone: ${entry_low:.2f} - ${entry_high:.2f}")
                            if entry_price is not None:
                                st.write(f"Entry Price: ${entry_price:.2f}")
                            if stop_loss is not None and stop_loss > 0:
                                st.write(f"Stop Loss: ${stop_loss:.2f}")
                        
                        with col2:
                            st.markdown("**Profit Targets**")
                            tp1 = card.get('take_profit_1')
                            tp2 = card.get('take_profit_2')
                            rr1 = card.get('rr_ratio_tp1')
                            rr2 = card.get('rr_ratio_tp2')
                            
                            if tp1 is not None and tp1 > 0:
                                st.write(f"TP1: ${tp1:.2f}" + (f" (RR: 1:{rr1:.2f})" if rr1 else ""))
                            if tp2 is not None and tp2 > 0:
                                st.write(f"TP2: ${tp2:.2f}" + (f" (RR: 1:{rr2:.2f})" if rr2 else ""))
                    else:
                        st.info(f"🔍 HOLD Signal - No trading setup generated (low confidence or conflicting signals)")
                    
                    st.divider()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Risk Management**")
                        leverage_rec = card.get('leverage_recommended')
                        leverage_max = card.get('leverage_max_mifid2')
                        st.write(f"Leverage Recommended: {leverage_rec}:1" if leverage_rec else "N/A")
                        st.write(f"MiFID II Max: {leverage_max}:1" if leverage_max else "N/A")
                        st.write(f"Timeframe: {card.get('timeframe', 'N/A')}")
                    
                    with col2:
                        st.markdown("**Technicals**")
                        rsi = card.get('rsi')
                        if rsi is not None:
                            st.write(f"RSI(14): {rsi:.2f}")
                        st.write(f"MACD Cross: {card.get('macd_cross', 'none')}")
                        st.write(f"Above 200 SMA: {card.get('above_200sma', False)}")
                    
                    st.divider()
                    
                    st.markdown("**Catalyst**")
                    catalyst = card.get('catalyst', 'No catalyst identified')
                    st.write(catalyst)
                    
                    st.markdown("**Sentiment**")
                    sentiment = card.get('sentiment_score')
                    if sentiment is not None:
                        st.write(f"Score: {sentiment:.2f}")
                    else:
                        st.write("Score: N/A")
                    
                    skip_reason = card.get('skip_reason')
                    if skip_reason:
                        st.warning(f"⚠️ Skip Reason: {skip_reason}")
            
            st.divider()
            
            # Export option
            st.subheader("Export Results")
        
        # Generate PDF
        def generate_pdf(trade_cards_data):
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=30,
                alignment=1  # Center
            )
            story.append(Paragraph("CFD Trading Signal Report", title_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Summary
            summary_data = [
                ["Total Signals", str(len(trade_cards_data))],
                ["BUY Signals", str(buy_count)],
                ["SELL Signals", str(sell_count)],
                ["HOLD Signals", str(hold_count)],
                ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f2f6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.5*inch))
            
            # Separate signals by type
            buy_signals = [card for card in trade_cards_data if card['signal'] == 'BUY']
            sell_signals = [card for card in trade_cards_data if card['signal'] == 'SELL']
            hold_signals = [card for card in trade_cards_data if card['signal'] == 'HOLD']
            
            # BUY SIGNALS - First Page
            if buy_signals:
                story.append(Paragraph("🟢 BUY STOCKS", ParagraphStyle('BUYHeading', parent=styles['Heading2'], textColor=colors.HexColor('#28a745'), spaceAfter=15)))
                story.append(Spacer(1, 0.2*inch))
                
                for card in buy_signals:
                    card_header = Paragraph(f"<b>{card['ticker']}</b> (Confidence: {card['confidence']}%)", styles['Heading3'])
                    story.append(card_header)
                    
                    card_data = [
                        ["Entry Price", f"${card.get('entry_price', 0):.2f}"],
                        ["Stop Loss", f"${card.get('stop_loss', 0):.2f}"],
                        ["TP1", f"${card.get('take_profit_1', 0):.2f}"],
                        ["TP2", f"${card.get('take_profit_2', 0):.2f}"],
                        ["Leverage", f"{card.get('leverage_recommended', 0)}:1"],
                        ["Catalyst", card.get('catalyst', 'N/A')[:80]]
                    ]
                    
                    card_table = Table(card_data, colWidths=[2*inch, 3.5*inch])
                    card_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#d4edda')),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#28a745'))
                    ]))
                    story.append(card_table)
                    story.append(Spacer(1, 0.3*inch))
            
            # Page break after BUY signals
            if sell_signals or hold_signals:
                story.append(PageBreak())
            
            # SELL SIGNALS
            if sell_signals:
                story.append(Paragraph("🔴 SELL STOCKS", ParagraphStyle('SELLHeading', parent=styles['Heading2'], textColor=colors.HexColor('#dc3545'), spaceAfter=15)))
                story.append(Spacer(1, 0.2*inch))
                
                for card in sell_signals:
                    card_header = Paragraph(f"<b>{card['ticker']}</b> (Confidence: {card['confidence']}%)", styles['Heading3'])
                    story.append(card_header)
                    
                    card_data = [
                        ["Entry Price", f"${card.get('entry_price', 0):.2f}"],
                        ["Stop Loss", f"${card.get('stop_loss', 0):.2f}"],
                        ["TP1", f"${card.get('take_profit_1', 0):.2f}"],
                        ["TP2", f"${card.get('take_profit_2', 0):.2f}"],
                        ["Leverage", f"{card.get('leverage_recommended', 0)}:1"],
                        ["Catalyst", card.get('catalyst', 'N/A')[:80]]
                    ]
                    
                    card_table = Table(card_data, colWidths=[2*inch, 3.5*inch])
                    card_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8d7da')),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dc3545'))
                    ]))
                    story.append(card_table)
                    story.append(Spacer(1, 0.3*inch))
            
            # Page break after SELL signals
            if hold_signals:
                story.append(PageBreak())
            
            # HOLD SIGNALS
            if hold_signals:
                story.append(Paragraph("🟡 HOLD STOCKS", ParagraphStyle('HOLDHeading', parent=styles['Heading2'], textColor=colors.HexColor('#ffc107'), spaceAfter=15)))
                story.append(Spacer(1, 0.2*inch))
                
                for card in hold_signals:
                    card_header = Paragraph(f"<b>{card['ticker']}</b> (Confidence: {card['confidence']}%)", styles['Heading3'])
                    story.append(card_header)
                    
                    card_data = [
                        ["Status", "HOLD - No trading setup"],
                        ["Catalyst", card.get('catalyst', 'N/A')[:80]],
                        ["Sentiment", f"{card.get('sentiment_score', 0):.2f}"],
                        ["RSI", f"{card.get('rsi', 0):.2f}"]
                    ]
                    
                    card_table = Table(card_data, colWidths=[2*inch, 3.5*inch])
                    card_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fff3cd')),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ffc107'))
                    ]))
                    story.append(card_table)
                    story.append(Spacer(1, 0.3*inch))
            
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
        
        # Generate and display PDF
        pdf_data = generate_pdf(results)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_data,
                file_name=f"trade_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                key="pdf_download"
            )
        
        with col2:
            # Excel Download Button
            excel_data = export_to_excel(results)
            st.download_button(
                label="📑 Download Excel",
                data=excel_data,
                file_name=f"trade_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="excel_download"
            )
        
        # ===== RIGHT COLUMN: CHAT WITH AGENTS =====
        with col_chat:
            st.markdown("### 🤖 Ask Agents")
            
            # Agent selection
            agent_type = st.radio(
                "Select Agent:",
                options=["📊 Trade Analyst", "📰 News Agent"],
                horizontal=True,
                key="agent_select"
            )
            
            # Map display names to agent types
            agent_map = {"📊 Trade Analyst": "analyst", "📰 News Agent": "news"}
            selected_agent = agent_map[agent_type]
            
            if selected_agent == "news":
                st.caption("Ask about headlines & sentiment (e.g., 'What's the news on AAPL?')")
            else:
                st.caption("Chat about trade signals & analysis")
            
            # Display chat history in a scrollable container
            with st.container(height=400, border=True):
                if len(st.session_state.chat_history) == 0:
                    st.caption("💬 No messages yet. Ask a question to get started!")
                else:
                    for msg in st.session_state.chat_history:
                        with st.chat_message(msg["role"], avatar="🧠" if msg["role"] == "assistant" else "👤"):
                            st.markdown(msg["content"])
            
            # Chat input section
            st.divider()
            
            # Initialize system for agent calls
            system = init_system()
            
            # Chat input field with custom key
            col_input, col_send = st.columns([4, 1])
            
            with col_input:
                user_question = st.text_input(
                    "Ask about these signals...",
                    placeholder="e.g., Why is AAPL a BUY? What about news on MSFT?",
                    key=f"agent_chat_input_{len(st.session_state.chat_history)}"
                )
            
            with col_send:
                send_button = st.button("Send", use_container_width=True, key=f"send_btn_{len(st.session_state.chat_history)}")
            
            if (user_question and send_button) or (user_question and st.session_state.get('send_clicked', False)):
                # Add user message to history
                st.session_state.chat_history.append({"role": "user", "content": user_question})
                st.session_state.send_clicked = False
                
                # Create placeholder for assistant response
                status_container = st.empty()
                
                try:
                    with status_container.status("🧠 Analyzing with agent...", expanded=True):
                        # Get agent response based on selected agent
                        answer = get_agent_answer(user_question, results, system, agent_type=selected_agent)
                        
                    # Add assistant message to history
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    
                    # Clear status and show success
                    status_container.success("✅ Response ready!")
                    
                except Exception as e:
                    error_msg = f"⚠️ Agent error: {str(e)[:150]}"
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                    status_container.error(f"Error: {str(e)[:100]}")
                
                # Force rerun to display new messages
                st.rerun()
    
    else:
        st.info("👈 Run a scan first to see trade card results")

# ==================== TAB 3: HISTORICAL ====================
with tab3:
    st.header("📁 Historical Signals")
    
    signals_dir = PROJECT_ROOT / "signals"
    
    # Look for both JSON and Excel files
    json_files = sorted(signals_dir.glob("signal_*.json"), reverse=True)
    excel_files = sorted(signals_dir.glob("signal_*.xlsx"), reverse=True)
    
    # Combine and sort
    all_files = json_files + excel_files
    all_files = sorted(all_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    if all_files:
        st.markdown(f"**Found {len(json_files)} JSON files + {len(excel_files)} Excel files**")
        
        selected_file = st.selectbox(
            "Select file:",
            all_files,
            format_func=lambda x: f"{x.name} ({'Excel' if x.suffix == '.xlsx' else 'JSON'})"
        )
        
        if selected_file:
            if selected_file.suffix == ".xlsx":
                # Load Excel file
                df = pd.read_excel(selected_file)
                
                # Show metadata
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Signals", len(df))
                with col2:
                    st.metric("BUY", len(df[df['Signal'] == 'BUY']))
                with col3:
                    st.metric("SELL", len(df[df['Signal'] == 'SELL']))
                with col4:
                    st.metric("HOLD", len(df[df['Signal'] == 'HOLD']))
                
                st.divider()
                
                # Display as table
                st.subheader("Trade Card Data")
                st.dataframe(df, use_container_width=True)
                
                # Download option
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 Re-download Excel",
                        data=selected_file.read_bytes(),
                        file_name=selected_file.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
            else:
                # Load JSON file
                with open(selected_file, 'r') as f:
                    data = json.load(f)
                
                # Show metadata
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Signals", data.get('total_signals', 0))
                with col2:
                    st.metric("BUY", data.get('buy_signals', 0))
                with col3:
                    st.metric("SELL", data.get('sell_signals', 0))
                with col4:
                    st.metric("HOLD", data.get('hold_signals', 0))
                
                st.divider()
                
                # Display trade cards
                trade_cards = data.get('trade_cards', [])
                
                for card in trade_cards:
                    signal = card['signal']
                    ticker = card['ticker']
                    confidence = card['confidence']
                    
                    if signal == 'BUY':
                        signal_icon = "🟢"
                    elif signal == 'SELL':
                        signal_icon = "🔴"
                    else:
                        signal_icon = "🟡"
                    
                    with st.expander(f"{signal_icon} {ticker} - {signal} ({confidence}%)"):
                        st.json(card)
                
                # Option to convert JSON to Excel
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📑 Convert to Excel", key="convert_to_excel"):
                        # Convert and download
                        excel_data = export_to_excel(trade_cards)
                        st.download_button(
                            label="📥 Download as Excel",
                            data=excel_data,
                            file_name=selected_file.stem + ".xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="json_to_excel"
                        )
    
    else:
        st.info("📁 No historical signal files found. Run a scan to generate signals.")

# ==================== TAB 4: ABOUT ====================
with tab4:
    st.header("ℹ️ About This System")
    
    st.markdown("""
    ## CFD Trading Signal System
    
    An AI-powered trading signal generation system using CrewAI agents and technical analysis.
    
    ### Architecture
    - **Daily Run**: Full scan at 08:00 Cairo time (UTC+2)
    - **Hourly Run**: Entry point monitoring when active signals exist
    - **AI Pipeline**: 4 CrewAI agents orchestrating research → synthesis → validation → portfolio
    - **Data**: Real-time pricing from yfinance + headlines from NewsAPI
    
    ### Signal Generation Flow
    
    1. **Python Layer** (No LLM)
       - Download OHLCV data
       - Calculate indicators (RSI, MACD, ATR, SMA)
       - Fetch 24h news headlines
       - Score sentiment using keyword analysis
       - Check earnings calendar
    
    2. **CrewAI Pipeline** (LLM-Driven)
       - **Task 1**: News Researcher identifies catalysts
       - **Task 2**: News Manager assigns confidence (gate at 65%)
       - **Task 3**: Stock Analyst validates technicals
       - **Task 4**: Portfolio Manager structures trade card
    
    ### Bullish Signal Conditions
    ALL must be true:
    - RSI(14) < 45
    - MACD bullish cross (last 3 candles)
    - Price above 200 SMA
    - Sentiment score > 0.2
    
    ### Bearish Signal Conditions
    ALL must be true:
    - RSI(14) > 58
    - MACD bearish cross (last 3 candles)
    - Price below 200 SMA
    - Sentiment score < -0.2
    
    ### Risk Management
    - **Entry Zone**: ±0.5 × ATR from current price
    - **Stop Loss**: 1.5 × ATR from entry
    - **TP1**: 2.0 × ATR (RR 1:1.33)
    - **TP2**: 4.0 × ATR (RR 1:2.67)
    - **Leverage**: MiFID II compliant (Stocks 5:1, Commodities 10:1, Crypto 2:1)
    
    ### Configuration
    - Edit `config.yaml` to customize watchlist, thresholds, and timing
    - Edit `.env` with your OpenAI and NewsAPI keys
    - All settings applied without restarting system
    
    ### Output Files
    - **Trade Cards**: `signals/signal_YYYYMMDD.json`
    - **Logs**: `trading_system.log`
    
    ### Tech Stack
    - CrewAI (AI orchestration)
    - yfinance (price data)
    - pandas_ta (technical indicators)
    - NewsAPI (financial headlines)
    - Streamlit (web UI)
    
    ---
    
    **Version**: 1.0.0  
    **Last Updated**: April 2024
    """)
    
    st.divider()
    
    st.markdown("### Quick Links")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📖 View README"):
            readme_path = PROJECT_ROOT / "README.md"
            if readme_path.exists():
                with open(readme_path) as f:
                    st.markdown(f.read())
    
    with col2:
        if st.button("⚙️ View Config"):
            config_path = PROJECT_ROOT / "config.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    st.code(f.read(), language="yaml")
    
    with col3:
        if st.button("📋 View Requirements"):
            req_path = PROJECT_ROOT / "requirements.txt"
            if req_path.exists():
                with open(req_path) as f:
                    st.code(f.read(), language="text")

st.divider()

# Footer
st.markdown("""
---
**CFD Trading Signal System** | Built with Streamlit & CrewAI  
⚠️ **Disclaimer**: For educational and research purposes only. Not financial advice. Always conduct your own due diligence.
""")
