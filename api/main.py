"""
Flask API for AI Traders - Converts Streamlit app to REST API
Same functionality as Streamlit app but deployable anywhere
"""

import sys
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json
from datetime import datetime

# Add trading_system to path
TRADING_SYSTEM = Path(__file__).parent.parent / "trading_system"
sys.path.insert(0, str(TRADING_SYSTEM))

# Import trading system modules
from analysis.sentiment import SentimentAnalyzer
from analysis.indicators import IndicatorCalculator
from agents.crew import CFDTradingCrew
from utils.duckduckgo_news import search_for_question
from config import INDUSTRIES, CONFIG

# Initialize Flask app
app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)
app.config['JSON_SORT_KEYS'] = False

# Initialize system components
sentiment_analyzer = SentimentAnalyzer()
indicator_calc = IndicatorCalculator()
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
    return jsonify({"stocks": INDUSTRIES[industry]})


@app.route('/api/analyze-stock', methods=['POST'])
def analyze_stock():
    """Analyze a single stock"""
    try:
        data = request.json
        ticker = data.get('ticker', '').upper()
        
        if not ticker:
            return jsonify({"error": "Ticker required"}), 400
        
        # Get sentiment and headlines
        sentiment_score = sentiment_analyzer.calculate_sentiment_score(ticker)
        headlines = sentiment_analyzer.get_top_headlines(ticker, limit=10)
        
        # Calculate indicators
        indicators = indicator_calc.calculate_all_indicators(ticker)
        
        # Run 3-pillar analysis
        three_pillar = calculate_three_pillars(
            ticker=ticker,
            indicators_data=indicators,
            sentiment_score=sentiment_score,
            headlines=headlines
        )
        
        return jsonify({
            "ticker": ticker,
            "sentiment": sentiment_score,
            "headlines": headlines,
            "indicators": indicators,
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
                
                three_pillar = calculate_three_pillars(
                    ticker=ticker,
                    indicators_data=indicators,
                    sentiment_score=sentiment,
                    headlines=headlines
                )
                
                results.append({
                    "ticker": ticker,
                    "signal": three_pillar.get("signal", "HOLD"),
                    "confidence": three_pillar.get("confidence", 0),
                    "sentiment": sentiment
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
def calculate_three_pillars(ticker, indicators_data, sentiment_score, headlines):
    """Calculate 3-pillar score (same logic as Streamlit app)"""
    
    # Technical Pillar (-1 to +1)
    rsi = indicators_data.get('rsi', 50)
    technical_score = 0
    
    if rsi < 35:
        technical_score += 0.4  # Oversold
    elif rsi > 65:
        technical_score -= 0.4  # Overbought
    else:
        technical_score += 0.1
    
    if indicators_data.get('macd_cross') == 'bullish':
        technical_score += 0.3
    elif indicators_data.get('macd_cross') == 'bearish':
        technical_score -= 0.3
    
    technical_score = max(-1, min(1, technical_score))
    
    # Qualitative Pillar (sentiment)
    qualitative_score = sentiment_score
    
    # Quantitative Pillar
    quantitative_score = 0
    if indicators_data.get('above_200sma'):
        quantitative_score += 0.25
    else:
        quantitative_score -= 0.25
    
    quantitative_score = max(-1, min(1, quantitative_score))
    
    # Combined score
    combined_score = (technical_score + qualitative_score + quantitative_score) / 3
    
    # Decision logic
    if combined_score > 0.4:
        signal = "BUY"
        confidence = min(0.95, 0.60 + (combined_score - 0.4) * 0.5)
    elif combined_score < -0.4:
        signal = "SELL"
        confidence = min(0.95, 0.60 + (abs(combined_score) - 0.4) * 0.5)
    else:
        signal = "HOLD"
        confidence = 0.30 + (abs(combined_score) * 1.0)
    
    return {
        "signal": signal,
        "confidence": confidence,
        "technical": technical_score,
        "qualitative": qualitative_score,
        "quantitative": quantitative_score,
        "combined_score": combined_score
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
