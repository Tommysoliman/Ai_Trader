"""
Flask API for AI Traders - Converts Streamlit app to REST API
Same functionality as Streamlit app but deployable anywhere
"""

import warnings
warnings.filterwarnings("ignore", message="Mixing V1 models and V2 models", category=UserWarning)

import sys
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json
from datetime import datetime

# Set up paths - use absolute paths from __file__
API_DIR = Path(__file__).parent
PROJECT_ROOT = API_DIR.parent
TRADING_SYSTEM = PROJECT_ROOT / "trading_system"

# Add trading_system to path for imports
sys.path.insert(0, str(TRADING_SYSTEM))
sys.path.insert(0, str(PROJECT_ROOT))

# Import trading system modules
from analysis.sentiment import SentimentAnalyzer
from analysis.indicators import IndicatorCalculator, get_fundamentals
from agents.crew import CFDTradingCrew
from utils.duckduckgo_news import search_for_question

# Define INDUSTRIES mapping (same as streamlit_app.py)
INDUSTRIES = {
    "⚡ Energy": ["XOM", "CVX", "COP", "MPC", "FANG"],
    "💻 Technology": ["NVDA", "MSFT", "META", "AAPL", "TSLA", "ORCL", "INTC", "GOOGL"],
    "🏦 Finance": ["JPM", "BAC", "GS", "WFC", "MS", "MA", "V"],
    "🛍️ Consumer": ["AMZN", "MCD", "PG", "NKE", "SBUX"],
    "📦 Commodities": ["GLD", "USO", "SLV", "FCX", "DBA"],
    "🇪🇬 Egypt": ["HRHO.CA", "BTFH.CA", "SWDY.CA", "MOIL.CA", "CCAP.CA", "COMI.CA", "CBKD.CA", "CIBEY.CA"]
}

STOCK_NAMES = {
    # Energy
    "XOM": "Exxon Mobil", "CVX": "Chevron", "COP": "ConocoPhillips",
    "MPC": "Marathon Petroleum", "FANG": "Diamondback Energy",
    # Technology
    "NVDA": "NVIDIA", "MSFT": "Microsoft", "META": "Meta Platforms",
    "AAPL": "Apple", "TSLA": "Tesla", "ORCL": "Oracle",
    "INTC": "Intel", "GOOGL": "Alphabet (Google)",
    # Finance
    "JPM": "JPMorgan Chase", "BAC": "Bank of America", "GS": "Goldman Sachs",
    "WFC": "Wells Fargo", "MS": "Morgan Stanley", "MA": "Mastercard", "V": "Visa",
    # Consumer
    "AMZN": "Amazon", "MCD": "McDonald's", "PG": "Procter & Gamble",
    "NKE": "Nike", "SBUX": "Starbucks",
    # Commodities
    "GLD": "SPDR Gold ETF", "USO": "US Oil Fund", "SLV": "iShares Silver Trust",
    "FCX": "Freeport-McMoRan", "DBA": "DB Agriculture ETF",
    # Egypt
    "HRHO.CA": "Heliopolis Housing", "BTFH.CA": "Beltone Financial",
    "SWDY.CA": "El Sewedy Electric", "MOIL.CA": "MOIL",
    "CCAP.CA": "Cairo Capital Brokerage", "COMI.CA": "Commercial Intl Bank",
    "CBKD.CA": "Credit Bank of Egypt", "CIBEY.CA": "CIB Egypt ADR"
}

# Default config (can be empty for now)
CONFIG = {}

# Initialize Flask app with absolute paths
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
CORS(app)
app.config['JSON_SORT_KEYS'] = False

# Initialize system components
sentiment_analyzer = SentimentAnalyzer(config=CONFIG)
indicator_calc = IndicatorCalculator(config=CONFIG)
crew = CFDTradingCrew(config=CONFIG)

# Store results in memory for session
session_results = {}


# ========== HOME / DASHBOARD ==========
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', industries=list(INDUSTRIES.keys()))


# ========== TAB 1: ANALYZE STOCK ==========
@app.route('/api/industries')
def get_industries():
    """Get list of industries"""
    return jsonify({"industries": list(INDUSTRIES.keys())})


@app.route('/api/stocks/<industry>')
def get_stocks(industry):
    """Get stocks for an industry"""
    if industry not in INDUSTRIES:
        return jsonify({"error": "Industry not found"}), 404
    stocks = [
        {"ticker": t, "name": STOCK_NAMES.get(t, t)}
        for t in INDUSTRIES[industry]
    ]
    return jsonify({"stocks": stocks})


@app.route('/api/analyze-stock', methods=['POST'])
def analyze_stock():
    """Analyze a single stock"""
    try:
        data = request.json
        ticker = data.get('ticker', '').upper()
        
        if not ticker:
            return jsonify({"error": "Ticker required"}), 400
        
        # Get sentiment and headlines
        try:
            sentiment_score = sentiment_analyzer.calculate_sentiment_score(ticker)
            headlines = sentiment_analyzer.get_top_headlines(ticker, limit=10)
        except Exception:
            sentiment_score = 0.0
            headlines = []

        # Calculate indicators
        indicators = indicator_calc.calculate_all_indicators(ticker)
        if indicators is None:
            return jsonify({"error": f"Could not fetch market data for {ticker}. Check the ticker symbol is valid."}), 400

        # Fetch fundamentals (earnings growth, P/E, revenue growth, etc.)
        fundamentals = get_fundamentals(ticker)

        # Run 3-pillar analysis
        three_pillar = calculate_three_pillars(
            ticker=ticker,
            indicators_data=indicators,
            sentiment_score=sentiment_score,
            headlines=headlines,
            fundamentals=fundamentals
        )

        safe_indicators = {k: v for k, v in indicators.items() if k != 'dataframe'}
        return jsonify({
            "ticker": ticker,
            "sentiment": sentiment_score,
            "headlines": headlines,
            "indicators": safe_indicators,
            "fundamentals": fundamentals,
            "analysis": three_pillar
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== TAB 2: DAILY SCAN ==========
@app.route('/api/daily-scan', methods=['POST'])
def daily_scan():
    """Scan multiple stocks"""
    try:
        data = request.json
        tickers = data.get('tickers', [])
        
        if not tickers:
            return jsonify({"error": "Tickers required"}), 400
        
        results = []
        for ticker in tickers:
            try:
                sentiment = sentiment_analyzer.calculate_sentiment_score(ticker)
                indicators = indicator_calc.calculate_all_indicators(ticker)
                headlines = sentiment_analyzer.get_top_headlines(ticker, limit=5)

                if indicators is None:
                    results.append({"ticker": ticker, "signal": "ERROR", "error": "No market data"})
                    continue

                fundamentals = get_fundamentals(ticker)
                three_pillar = calculate_three_pillars(
                    ticker=ticker,
                    indicators_data=indicators,
                    sentiment_score=sentiment,
                    headlines=headlines,
                    fundamentals=fundamentals
                )

                results.append({
                    "ticker": ticker,
                    "signal": three_pillar.get("signal", "HOLD"),
                    "confidence": three_pillar.get("confidence", 0),
                    "sentiment": sentiment,
                    "technical": three_pillar.get("technical", 0),
                    "qualitative": three_pillar.get("qualitative", 0),
                    "quantitative": three_pillar.get("quantitative", 0),
                    "combined_score": three_pillar.get("combined_score", 0)
                })
            except Exception as e:
                results.append({
                    "ticker": ticker,
                    "error": str(e)
                })
        
        # Store for tab 3
        session_results['scan_results'] = results
        session_results['scan_time'] = datetime.now().isoformat()
        
        return jsonify({"results": results})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== TAB 3: RESULTS ==========
@app.route('/api/results')
def get_results():
    """Get stored scan results"""
    if 'scan_results' not in session_results:
        return jsonify({"error": "No results available. Run daily scan first."}), 400
    
    return jsonify({
        "results": session_results.get('scan_results', []),
        "timestamp": session_results.get('scan_time', '')
    })


@app.route('/api/export-excel')
def export_excel():
    """Export results to Excel"""
    try:
        import pandas as pd
        from io import BytesIO
        
        if 'scan_results' not in session_results:
            return jsonify({"error": "No results to export"}), 400
        
        df = pd.DataFrame(session_results['scan_results'])
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Results', index=False)
        
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'trading_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== TAB 4: NEWS Q&A ==========
@app.route('/api/qa', methods=['POST'])
def ask_question():
    """Answer market questions using DuckDuckGo + CrewAI"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({"error": "Question required"}), 400
        
        # Search for relevant news
        news_context = search_for_question(question, num_results=10)
        if not news_context or not news_context.strip():
            news_context = "No recent news found. Please answer based on general market knowledge."

        # Get AI answer from CrewAI
        answer = crew.run_market_qa(question, news_context)
        
        return jsonify({
            "question": question,
            "answer": answer,
            "context": news_context
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stock-qa', methods=['POST'])
def stock_qa():
    """Q&A for specific stock"""
    try:
        data = request.json
        ticker = data.get('ticker', '').upper()
        question = data.get('question', '').strip()
        
        if not ticker or not question:
            return jsonify({"error": "Ticker and question required"}), 400
        
        # Fetch news for stock
        sentiment = sentiment_analyzer.calculate_sentiment_score(ticker)
        headlines = sentiment_analyzer.get_top_headlines(ticker, limit=10)
        
        # Run signal generation (includes Q&A analysis)
        indicators = indicator_calc.calculate_all_indicators(ticker)
        if indicators is None:
            return jsonify({"error": f"Could not fetch market data for {ticker}. Check the ticker symbol is valid."}), 400

        analysis = crew.run_signal_generation(
            ticker=ticker,
            indicators_data=indicators,
            sentiment_score=sentiment,
            top_headlines=headlines
        )
        
        return jsonify({
            "ticker": ticker,
            "question": question,
            "analysis": analysis,
            "headlines": headlines[:5]
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== TAB 5: ABOUT ==========
@app.route('/api/framework')
def get_framework():
    """Get 3-pillar framework info"""
    return jsonify({
        "framework": {
            "name": "3-Pillar Trading Framework",
            "pillars": [
                {
                    "name": "Technical Analysis",
                    "emoji": "📊",
                    "description": "RSI, MACD, Volume, ATR indicators",
                    "range": "-1 to +1"
                },
                {
                    "name": "Qualitative Analysis",
                    "emoji": "📰",
                    "description": "News sentiment from headlines",
                    "range": "-1 to +1"
                },
                {
                    "name": "Quantitative Analysis",
                    "emoji": "💹",
                    "description": "Price, MA, EPS, earnings growth",
                    "range": "-1 to +1"
                }
            ],
            "decision_logic": {
                "BUY": "Combined score > 0.4",
                "SELL": "Combined score < -0.4",
                "HOLD": "Score between -0.4 and +0.4"
            }
        }
    })


# ========== HELPER FUNCTIONS ==========
def calculate_three_pillars(ticker, indicators_data, sentiment_score, headlines, fundamentals=None):
    """
    3-Pillar scoring model (-1 to +1 per pillar):

    Pillar 1 — TECHNICAL  : RSI, MACD cross, Volume surge, SMA alignment
    Pillar 2 — QUALITATIVE: News sentiment score from headlines
    Pillar 3 — QUANTITATIVE: Earnings growth, revenue growth, P/E, ROE, analyst target
    """
    if indicators_data is None:
        return {"signal": "HOLD", "confidence": 0.0, "technical": 0.0,
                "qualitative": 0.0, "quantitative": 0.0, "combined_score": 0.0}

    # ── PILLAR 1: TECHNICAL ──────────────────────────────────────────────────
    technical_score = 0.0

    # RSI (weight: 0.35)
    rsi = indicators_data.get('rsi', 50)
    if rsi < 30:
        technical_score += 0.35       # strongly oversold → bullish
    elif rsi < 45:
        technical_score += 0.20       # mildly oversold
    elif rsi > 70:
        technical_score -= 0.35       # strongly overbought → bearish
    elif rsi > 58:
        technical_score -= 0.20       # mildly overbought

    # MACD cross (weight: 0.25)
    if indicators_data.get('macd_cross') == 'bullish':
        technical_score += 0.25
    elif indicators_data.get('macd_cross') == 'bearish':
        technical_score -= 0.25

    # Volume surge — above 1.5× 20-day average = conviction (weight: 0.20)
    volume_ratio = indicators_data.get('volume_ratio', 1.0)
    if volume_ratio >= 1.5:
        technical_score += 0.20       # high volume confirms move
    elif volume_ratio <= 0.6:
        technical_score -= 0.10       # low volume = weak conviction

    # SMA alignment (weight: 0.20)
    if indicators_data.get('golden_cross'):           # SMA-50 > SMA-200
        technical_score += 0.10
    if indicators_data.get('above_200sma'):           # price above long-term trend
        technical_score += 0.10
    if not indicators_data.get('above_200sma'):
        technical_score -= 0.10
    if not indicators_data.get('golden_cross'):
        technical_score -= 0.05

    technical_score = max(-1.0, min(1.0, technical_score))

    # ── PILLAR 2: QUALITATIVE (news sentiment) ───────────────────────────────
    qualitative_score = max(-1.0, min(1.0, float(sentiment_score or 0.0)))

    # ── PILLAR 3: QUANTITATIVE (financial performance) ───────────────────────
    quantitative_score = 0.0
    fundamentals = fundamentals or {}

    # Earnings growth (weight: 0.35)
    eg = fundamentals.get('earnings_growth')
    if eg is not None:
        if eg > 0.20:
            quantitative_score += 0.35    # strong growth > 20%
        elif eg > 0.05:
            quantitative_score += 0.15    # moderate growth
        elif eg < 0:
            quantitative_score -= 0.35    # earnings declining

    # Revenue growth (weight: 0.25)
    rg = fundamentals.get('revenue_growth')
    if rg is not None:
        if rg > 0.15:
            quantitative_score += 0.25
        elif rg > 0.0:
            quantitative_score += 0.10
        elif rg < 0:
            quantitative_score -= 0.25

    # P/E vs forward P/E — forward < trailing means improving earnings (weight: 0.20)
    trailing_pe = fundamentals.get('trailing_pe')
    forward_pe  = fundamentals.get('forward_pe')
    if trailing_pe and forward_pe and trailing_pe > 0 and forward_pe > 0:
        if forward_pe < trailing_pe * 0.9:
            quantitative_score += 0.20    # earnings expected to improve
        elif forward_pe > trailing_pe * 1.1:
            quantitative_score -= 0.10    # earnings expected to worsen

    # Analyst consensus target vs current price (weight: 0.20)
    target = fundamentals.get('analyst_target')
    price  = indicators_data.get('current_price', 0)
    if target and price and price > 0:
        upside = (target - price) / price
        if upside > 0.15:
            quantitative_score += 0.20    # >15% analyst upside
        elif upside > 0.05:
            quantitative_score += 0.10
        elif upside < -0.05:
            quantitative_score -= 0.20    # analysts see downside

    quantitative_score = max(-1.0, min(1.0, quantitative_score))

    # ── COMBINED SCORE & SIGNAL ───────────────────────────────────────────────
    combined_score = (technical_score + qualitative_score + quantitative_score) / 3.0

    if combined_score > 0.35:
        signal = "BUY"
        confidence = min(0.95, 0.60 + (combined_score - 0.35) * 0.6)
    elif combined_score < -0.35:
        signal = "SELL"
        confidence = min(0.95, 0.60 + (abs(combined_score) - 0.35) * 0.6)
    else:
        signal = "HOLD"
        confidence = 0.30 + abs(combined_score)

    return {
        "signal": signal,
        "confidence": round(confidence, 3),
        "technical": round(technical_score, 3),
        "qualitative": round(qualitative_score, 3),
        "quantitative": round(quantitative_score, 3),
        "combined_score": round(combined_score, 3),
        "breakdown": {
            "rsi": rsi,
            "macd": indicators_data.get('macd_cross', 'none'),
            "volume_ratio": volume_ratio,
            "golden_cross": indicators_data.get('golden_cross', False),
            "above_200sma": indicators_data.get('above_200sma', False),
            "earnings_growth": eg,
            "revenue_growth": rg,
            "analyst_target": target,
        }
    }


# ========== ERROR HANDLERS ==========
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ========== HEALTH CHECK ==========
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "AI Traders API"})


if __name__ == '__main__':
    # Run with gunicorn in production
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 8000)))
