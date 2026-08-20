"""
Flask API for AI Traders - Converts Streamlit app to REST API
Same functionality as Streamlit app but deployable anywhere
"""

import warnings
warnings.filterwarnings("ignore", message="Mixing V1 models and V2 models", category=UserWarning)

import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json
from datetime import datetime, timedelta
import yfinance as yf

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

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
from analysis.ml_scorer import get_ml_scorer, SECTOR_ETFS, fetch_ohlcv_cached
from analysis.earnings import EarningsChecker
from agents.crew import CFDTradingCrew
from utils.duckduckgo_news import search_for_question

# Define INDUSTRIES mapping (same as streamlit_app.py)
INDUSTRIES = {
    "⚡ Energy": ["XOM", "CVX", "COP", "MPC", "FANG"],
    "💻 Technology": ["NVDA", "MSFT", "META", "AAPL", "TSLA", "ORCL", "INTC", "GOOGL", "BABA", "PDD"],
    "🏦 Finance": ["JPM", "BAC", "GS", "WFC", "MS", "MA", "V"],
    "🛍️ Consumer": ["AMZN", "MCD", "PG", "NKE", "SBUX"],
    "📦 Commodities": ["GLD", "USO", "SLV", "FCX", "DBA"],
    "🇪🇬 Egypt": ["HRHO.CA", "BTFH.CA", "SWDY.CA", "MOIL.CA", "CCAP.CA", "COMI.CA"]
}

STOCK_NAMES = {
    # Energy
    "XOM": "Exxon Mobil", "CVX": "Chevron", "COP": "ConocoPhillips",
    "MPC": "Marathon Petroleum", "FANG": "Diamondback Energy",
    # Technology
    "NVDA": "NVIDIA", "MSFT": "Microsoft", "META": "Meta Platforms",
    "AAPL": "Apple", "TSLA": "Tesla", "ORCL": "Oracle",
    "INTC": "Intel", "GOOGL": "Alphabet (Google)", "BABA": "Alibaba", "PDD": "PDD Holdings (Temu)",
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
}

# Default config (can be empty for now)
CONFIG = {}

# The only three signal labels exposed by the Flask API and Daily Scan.
BUY_OUTPUT = "Buy"
SELL_OUTPUT = "Sell"
RISK_OUTPUT = "Not worth taking the risk"


def public_signal(signal):
    """Normalize internal, legacy, ML, and error states to three outputs."""
    value = str(signal or "").strip().lower()
    if value == "buy":
        return BUY_OUTPUT
    if value == "sell":
        return SELL_OUTPUT
    return RISK_OUTPUT

# ── Risk management configuration ────────────────────────────────────────────
ACCOUNT_SIZE      = 100_000   # USD — change this to your actual account size
ATR_STOP_MULT     = 1.5       # stop loss = entry ± (ATR × this)
MIN_RR_RATIO      = 1.5       # signals with R:R below this are suppressed
RISK_PCT_PER_TRADE = 0.01     # 1% of account risked per trade

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

# Scan progress state — polled by /api/scan-progress
_scan_progress = {"total": 0, "done": 0, "running": False, "current": ""}
_scan_progress_lock = threading.Lock()

_earnings_checker = EarningsChecker(config={"earnings": {"skip_within_days": 7}})


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

def _analyze_one(ticker: str) -> dict:
    """Analyze a single ticker — designed to run inside a thread pool."""
    with _scan_progress_lock:
        _scan_progress["current"] = ticker

    try:
        sentiment  = sentiment_analyzer.calculate_sentiment_score(ticker)
        indicators = indicator_calc.calculate_all_indicators(ticker)
        headlines  = sentiment_analyzer.get_top_headlines(ticker, limit=5)

        if indicators is None:
            return {
                "ticker": ticker,
                "signal": RISK_OUTPUT,
                "status": "error",
                "decision_reason": "Market data could not be retrieved",
                "error": "No market data",
            }

        fundamentals = get_fundamentals(ticker)
        three_pillar = calculate_three_pillars(
            ticker=ticker,
            indicators_data=indicators,
            sentiment_score=sentiment,
            headlines=headlines,
            fundamentals=fundamentals,
        )

        return {
            "ticker":        ticker,
            "signal":        public_signal(three_pillar.get("signal")),
            "confidence":    three_pillar.get("confidence", 0),
            "sentiment":     sentiment,
            "technical":     three_pillar.get("technical", 0),
            "qualitative":   three_pillar.get("qualitative", 0),
            "quantitative":  three_pillar.get("quantitative", 0),
            "ml_score":      three_pillar.get("ml_score", 0),
            "combined_score": three_pillar.get("combined_score", 0),
            "signal_source": three_pillar.get("signal_source", "rule-based only"),
            "status":         "ok",
            "decision_reason": three_pillar.get("decision_reason", "Risk filters rejected the setup"),
            "flag":           three_pillar.get("flag"),
            "ml":            three_pillar.get("ml", {}),
        }
    except Exception as e:
        print(f"[DAILY SCAN] {ticker} failed: {e}")
        return {
            "ticker": ticker,
            "signal": RISK_OUTPUT,
            "status": "error",
            "decision_reason": "Analysis failed; no trade should be taken",
            "error": str(e),
        }
    finally:
        with _scan_progress_lock:
            _scan_progress["done"] += 1


@app.route('/api/scan-progress')
def scan_progress():
    """Poll this endpoint to get live progress during a daily scan."""
    with _scan_progress_lock:
        return jsonify(dict(_scan_progress))


@app.route('/api/daily-scan', methods=['POST'])
def daily_scan():
    """Scan multiple stocks in parallel (up to 5 concurrent workers)."""
    try:
        data    = request.json
        tickers = data.get('tickers', [])

        if not tickers:
            return jsonify({"error": "Tickers required"}), 400

        # Reset progress counter
        with _scan_progress_lock:
            _scan_progress.update({"total": len(tickers), "done": 0,
                                   "running": True, "current": ""})

        results = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(_analyze_one, t): t for t in tickers}
            for future in tqdm(as_completed(futures), total=len(futures),
                               desc="Scanning", unit="stock"):
                results.append(future.result())

        # Sort back into original ticker order
        order = {t: i for i, t in enumerate(tickers)}
        results.sort(key=lambda r: order.get(r.get("ticker", ""), 999))

        with _scan_progress_lock:
            _scan_progress.update({"running": False, "current": ""})

        session_results['scan_results'] = results
        session_results['scan_time']    = datetime.now().isoformat()

        summary = {
            "Buy": sum(r.get("signal") == BUY_OUTPUT for r in results),
            "Sell": sum(r.get("signal") == SELL_OUTPUT for r in results),
            "Not worth taking the risk": sum(r.get("signal") == RISK_OUTPUT for r in results),
            "errors": sum(r.get("status") == "error" for r in results),
        }
        print(f"[DAILY SCAN] completed: {summary}")
        return jsonify({"results": results, "summary": summary})

    except Exception as e:
        with _scan_progress_lock:
            _scan_progress["running"] = False
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

def _apply_rr_filter(signal: str, entry: float, atr: float, df) -> dict | None:
    """
    Compute ATR-based stop loss, 20-period high/low target, and R:R ratio.

    Returns a dict with trade levels and position size.
    Returns None if inputs are invalid.
    The 'sufficient' key is False when R:R < MIN_RR_RATIO.
    """
    if not entry or entry <= 0 or not atr or atr <= 0:
        return None
    if df is None or len(df) < 20:
        return None

    stop_dist = ATR_STOP_MULT * atr

    if signal == "BUY":
        stop_loss    = round(entry - stop_dist, 2)
        # Resistance = highest High in last 20 periods
        target_price = round(float(df["High"].tail(20).max()), 2)
        risk         = entry - stop_loss
        reward       = target_price - entry
    elif signal == "SELL":
        stop_loss    = round(entry + stop_dist, 2)
        # Support = lowest Low in last 20 periods
        target_price = round(float(df["Low"].tail(20).min()), 2)
        risk         = stop_loss - entry
        reward       = entry - target_price
    else:
        return None

    if risk <= 0 or reward <= 0:
        # Target is on the wrong side of entry (e.g. price already at 20-period high)
        return {"sufficient": False, "rr_ratio": 0.0, "reason": "target not beyond entry"}

    rr = round(reward / risk, 2)

    if rr < MIN_RR_RATIO:
        return {"sufficient": False, "rr_ratio": rr}

    # Position size: (account × risk%) / risk-per-share
    risk_amount   = ACCOUNT_SIZE * RISK_PCT_PER_TRADE
    position_size = max(1, int(risk_amount / risk))

    return {
        "sufficient":     True,
        "entry":          round(entry, 2),
        "stop_loss":      stop_loss,
        "target":         target_price,
        "rr_ratio":       rr,
        "risk_per_share": round(risk, 2),
        "position_size":  position_size,
        "account_risk_usd": round(risk_amount, 2),
    }


def calculate_three_pillars(ticker, indicators_data, sentiment_score, headlines, fundamentals=None):
    """
    3-Pillar scoring model (-1 to +1 per pillar):
      Pillar 1 — TECHNICAL   : RSI, MACD, volume, SMA, ATR expansion, sector RS
      Pillar 2 — QUALITATIVE : news sentiment
      Pillar 3 — QUANTITATIVE: earnings/revenue growth, P/E, analyst target

    Extras:
      - Earnings proximity guard (7-day binary event risk)
      - 3-indicator confidence filter (Mixed Signal if < 3 agree)
      - ML layer (Random Forest) reconciled with rule-based signal
    """
    if indicators_data is None:
        return {"signal": RISK_OUTPUT, "confidence": 0.0, "technical": 0.0,
                "qualitative": 0.0, "quantitative": 0.0, "combined_score": 0.0,
                "decision_reason": "Market data is unavailable"}

    fundamentals = fundamentals or {}

    # ── EARNINGS PROXIMITY CHECK ─────────────────────────────────────────────
    try:
        skip, earnings_date = _earnings_checker.check_earnings_within_threshold(ticker)
    except Exception:
        skip, earnings_date = False, None

    if skip:
        return {
            "signal": RISK_OUTPUT,
            "confidence": 0.0,
            "technical": 0.0, "qualitative": 0.0, "quantitative": 0.0,
            "combined_score": 0.0,
            "decision_reason": f"Earnings event risk on {earnings_date}",
            "flag": f"BINARY EVENT RISK — earnings on {earnings_date}",
            "signal_source": "rule-based only",
            "ml": {},
            "breakdown": {},
        }

    # ── PILLAR 1: TECHNICAL ──────────────────────────────────────────────────
    technical_score = 0.0
    votes = []  # +1 bullish, -1 bearish, 0 neutral — for confidence filter

    # RSI (weight: 0.35)
    # Strong signals: <20 oversold, >80 overbought
    # Momentum signals: 50-75 = trending up (bullish vote), 35-50 = trending down (bearish vote)
    rsi = indicators_data.get('rsi', 50)
    if rsi < 20:
        technical_score += 0.35
        votes.append(1)
    elif rsi < 35:
        technical_score += 0.20
        votes.append(1)
    elif rsi > 80:
        technical_score -= 0.35
        votes.append(-1)
    elif rsi > 75:
        technical_score -= 0.20
        votes.append(-1)
    elif rsi > 50:
        votes.append(1)   # upward momentum — counts toward confidence filter
    elif rsi < 50:
        votes.append(-1)  # downward momentum
    else:
        votes.append(0)

    # MACD cross (weight: 0.25)
    macd = indicators_data.get('macd_cross', 'none')
    if macd == 'bullish':
        technical_score += 0.25
        votes.append(1)
    elif macd == 'bearish':
        technical_score -= 0.25
        votes.append(-1)
    else:
        votes.append(0)

    # Volume vs 20-day average (weight: 0.20)
    volume_ratio = indicators_data.get('volume_ratio', 1.0)
    price_change_pct = indicators_data.get('price_change_pct', 0.0)
    if volume_ratio >= 1.5:
        if price_change_pct > 0:
            technical_score += 0.20
            votes.append(1)
        elif price_change_pct < 0:
            technical_score -= 0.20
            votes.append(-1)
        else:
            votes.append(0)
    else:
        votes.append(0)

    # SMA alignment — golden cross weight reduced to 0.05 (lagging indicator)
    golden_cross  = indicators_data.get('golden_cross', False)
    above_200sma  = indicators_data.get('above_200sma', False)
    if golden_cross:
        technical_score += 0.05
        votes.append(1)
    else:
        technical_score -= 0.05
        votes.append(-1)
    if above_200sma:
        technical_score += 0.10
    else:
        technical_score -= 0.10

    # ATR expansion — current ATR > 20-day avg ATR × 1.1 = momentum confirmation (+0.10)
    atr_expanding = False
    df = indicators_data.get('dataframe')
    if df is not None and len(df) >= 20:
        try:
            from analysis.indicators import IndicatorCalculator as _IC
            _atr = _IC().calculate_atr(df)
            if not _atr.iloc[-1:].isna().any():
                atr_now = float(_atr.iloc[-1])
                atr_avg = float(_atr.iloc[-20:].mean())
                if atr_now > atr_avg * 1.1:
                    atr_expanding = True
                    if price_change_pct > 0:
                        technical_score += 0.10
                        votes.append(1)
                    elif price_change_pct < 0:
                        technical_score -= 0.10
                        votes.append(-1)
                    else:
                        votes.append(0)
                else:
                    votes.append(0)
        except Exception:
            votes.append(0)
    else:
        votes.append(0)

    # Sector relative strength — outperforming ETF by >2% over 20 days = +0.15
    sector_outperforming = False
    rs_vs_sector = None
    sector_etf = SECTOR_ETFS.get(fundamentals.get('sector', ''))
    if sector_etf and df is not None and len(df) >= 20:
        try:
            etf_df = fetch_ohlcv_cached(sector_etf, period="1y")
            if etf_df is not None and len(etf_df) >= 20:
                if hasattr(etf_df.columns, 'levels'):
                    etf_df = etf_df.droplevel(1, axis=1)
                stock_ret = float(df['Close'].iloc[-1]) / float(df['Close'].iloc[-20]) - 1
                etf_ret   = float(etf_df['Close'].iloc[-1]) / float(etf_df['Close'].iloc[-20]) - 1
                rs_vs_sector = round(stock_ret - etf_ret, 4)
                if rs_vs_sector > 0.02:
                    technical_score += 0.15
                    sector_outperforming = True
                    votes.append(1)
                elif rs_vs_sector < -0.02:
                    technical_score -= 0.10
                    votes.append(-1)
                else:
                    votes.append(0)
        except Exception:
            votes.append(0)
    else:
        votes.append(0)

    technical_score = max(-1.0, min(1.0, technical_score))

    # ── PILLAR 2: QUALITATIVE (news sentiment) ───────────────────────────────
    qualitative_score = max(-1.0, min(1.0, float(sentiment_score or 0.0)))

    # ── PILLAR 3: QUANTITATIVE (financial performance) ───────────────────────
    quantitative_score = 0.0

    eg = fundamentals.get('earnings_growth')
    if eg is not None:
        if eg > 0.20:
            quantitative_score += 0.35
        elif eg > 0.05:
            quantitative_score += 0.15
        elif eg < 0:
            quantitative_score -= 0.35

    rg = fundamentals.get('revenue_growth')
    if rg is not None:
        if rg > 0.15:
            quantitative_score += 0.25
        elif rg > 0.0:
            quantitative_score += 0.10
        elif rg < 0:
            quantitative_score -= 0.25

    trailing_pe = fundamentals.get('trailing_pe')
    forward_pe  = fundamentals.get('forward_pe')
    if trailing_pe and forward_pe and trailing_pe > 0 and forward_pe > 0:
        if forward_pe < trailing_pe * 0.9:
            quantitative_score += 0.20
        elif forward_pe > trailing_pe * 1.1:
            quantitative_score -= 0.10

    target = fundamentals.get('analyst_target')
    price  = indicators_data.get('current_price', 0)
    if target and price and price > 0:
        upside = (target - price) / price
        if upside > 0.15:
            quantitative_score += 0.20
        elif upside > 0.05:
            quantitative_score += 0.10
        elif upside < -0.05:
            quantitative_score -= 0.20

    quantitative_score = max(-1.0, min(1.0, quantitative_score))

    # ── COMBINED SCORE ────────────────────────────────────────────────────────
    combined_score = (technical_score * 0.5) + (qualitative_score * 0.3) + (quantitative_score * 0.2)

    # ── CONFIDENCE FILTER: require 3+ indicators pointing same direction ─────
    bullish_votes = votes.count(1)
    bearish_votes = votes.count(-1)

    # ── PILLAR 4: ML (Random Forest probability → -1 to +1) ──────────────────
    ml_result  = None
    ml_score   = 0.0
    ml_reliable = False
    if df is not None:
        try:
            ml_result = get_ml_scorer().predict(ticker, df, sector_etf)
        except Exception as e:
            print(f"[ML] Prediction error for {ticker}: {e}")

    if ml_result and ml_result.get('model_reliable'):
        ml_reliable = True
        prob     = ml_result.get('ml_probability', 0.5)
        ml_score = round((prob - 0.5) * 2, 3)   # 0.65→+0.30, 0.80→+0.60, 0.35→-0.30

    # ── COMBINED SCORE (4-pillar) ─────────────────────────────────────────────
    # Weights: tech 35%, qual 10%, quant 20%, ml 35%
    # If ML is unavailable fall back to 3-pillar weights (50/20/30)
    if ml_reliable:
        combined_score = (
            (technical_score    * 0.35) +
            (qualitative_score  * 0.10) +
            (quantitative_score * 0.20) +
            (ml_score           * 0.35)
        )
        signal_source = "4-pillar (ML included)"
    else:
        combined_score = (
            (technical_score    * 0.50) +
            (qualitative_score  * 0.20) +
            (quantitative_score * 0.30)
        )
        signal_source = "3-pillar (ML unavailable)"

    # ── CONFIDENCE FILTER: require 3+ indicators pointing same direction ──────
    if combined_score > 0.35 and bullish_votes >= 3:
        signal     = "BUY"
        confidence = min(0.95, 0.60 + (combined_score - 0.35) * 0.6)
        decision_reason = f"Bullish score with {bullish_votes} confirming indicators"
    elif combined_score < -0.35 and bearish_votes >= 3:
        signal     = "SELL"
        confidence = min(0.95, 0.60 + (abs(combined_score) - 0.35) * 0.6)
        decision_reason = f"Bearish score with {bearish_votes} confirming indicators"
    else:
        signal     = RISK_OUTPUT
        confidence = 0.30 + abs(combined_score)
        if abs(combined_score) <= 0.35:
            decision_reason = f"Combined score {combined_score:.3f} lacks a strong direction"
        elif combined_score > 0:
            decision_reason = f"Only {bullish_votes} bullish indicators agree; 3 required"
        else:
            decision_reason = f"Only {bearish_votes} bearish indicators agree; 3 required"

    final_signal = signal

    # ── MARKET REGIME FILTER ──────────────────────────────────────────────────
    # Suppress BUY signals when the broad market (SPY) is in a downtrend.
    # SPY data uses the same 24h cache — no extra latency.
    if final_signal == "BUY":
        try:
            spy_df = fetch_ohlcv_cached("SPY", period="1y")
            if spy_df is not None and len(spy_df) >= 200:
                if hasattr(spy_df.columns, "levels"):
                    spy_df = spy_df.droplevel(1, axis=1)
                spy_close   = spy_df["Close"].squeeze().astype(float)
                spy_sma200  = spy_close.rolling(200).mean().iloc[-1]
                spy_current = spy_close.iloc[-1]
                if spy_current < spy_sma200:
                    final_signal  = RISK_OUTPUT
                    decision_reason = "Bullish setup suppressed because SPY is below its 200-day SMA"
                    signal_source += " [REGIME: SPY below 200-SMA — BUY suppressed]"
        except Exception:
            pass

    # ── R:R FILTER ────────────────────────────────────────────────────────────
    entry   = indicators_data.get('current_price', 0)
    atr_val = indicators_data.get('atr', 0)
    trade_levels = None

    if final_signal in ('BUY', 'SELL'):
        trade_levels = _apply_rr_filter(final_signal, entry, atr_val, df)
        if trade_levels is None or not trade_levels.get('sufficient'):
            rr_shown     = (trade_levels or {}).get('rr_ratio', 'N/A')
            final_signal = RISK_OUTPUT
            decision_reason = f"Risk/reward {rr_shown} is below the required {MIN_RR_RATIO}"
            signal_source += f" [R:R={rr_shown} < {MIN_RR_RATIO}]"

    # Confidence level string: "X/N indicators agree"
    total_votes      = len(votes)
    agreeing_count   = max(bullish_votes, bearish_votes)
    confidence_level = f"{agreeing_count}/{total_votes} indicators agree"

    return {
        "signal":            public_signal(final_signal),
        "confidence":        round(confidence, 3),
        "confidence_level":  confidence_level,
        "technical":         round(technical_score, 3),
        "qualitative":       round(qualitative_score, 3),
        "quantitative":      round(quantitative_score, 3),
        "ml_score":          round(ml_score, 3),
        "combined_score":    round(combined_score, 3),
        "signal_source":     signal_source,
        "decision_reason":   decision_reason,
        "ml":                ml_result or {},
        "trade":             trade_levels or {},
        "breakdown": {
            "rsi":                  rsi,
            "macd":                 macd,
            "volume_ratio":         volume_ratio,
            "golden_cross":         golden_cross,
            "above_200sma":         above_200sma,
            "atr_expanding":        atr_expanding,
            "sector_outperforming": sector_outperforming,
            "rs_vs_sector":         rs_vs_sector,
            "indicator_votes":      {"bullish": bullish_votes, "bearish": bearish_votes,
                                     "total": total_votes},
            "earnings_growth":      eg,
            "revenue_growth":       rg,
            "analyst_target":       target,
        },
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
