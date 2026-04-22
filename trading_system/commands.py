#!/usr/bin/env python3
"""
COMMAND LAUNCHER - Copy & Paste Ready Commands for Trading System

This file contains ready-to-copy commands for common operations.
Just copy the command from your terminal's context and paste.
"""

# ============================================================================
# SETUP COMMANDS (Run First)
# ============================================================================

SETUP_INSTALL = """
pip install -r requirements.txt
"""

SETUP_EDIT_ENV = """
nano .env

# Then add:
# OPENAI_API_KEY=sk-your-key
# NEWSAPI_KEY=your-key
"""

SETUP_VERIFY = """
python -m py_compile main.py analysis/*.py agents/*.py utils/*.py
"""

# ============================================================================
# RUN COMMANDS (Choose One)
# ============================================================================

RUN_WEB_UI_ONLY = """
streamlit run streamlit_app.py
"""

RUN_SCHEDULER_BACKGROUND = """
python main.py
"""

RUN_BOTH_TERMINALS = """
# Terminal 1 - Start scheduler
python main.py

# Terminal 2 - Start web UI
streamlit run streamlit_app.py
"""

# ============================================================================
# ANALYSIS COMMANDS
# ============================================================================

ANALYZE_SINGLE_TICKER = """
# From Python shell within streamlit app
# Or from terminal (modify for local execution):
python -c "
from analysis.indicators import IndicatorCalculator
from analysis.sentiment import SentimentAnalyzer

calc = IndicatorCalculator()
sentiment = SentimentAnalyzer()

ticker = 'ORCL'
ind = calc.calculate_all_indicators(ticker)
sent = sentiment.calculate_sentiment_score(ticker)

print(f'{ticker}: RSI={ind[\"rsi\"]:.1f}, Sentiment={sent:.2f}')
"
"""

# ============================================================================
# MONITORING COMMANDS
# ============================================================================

MONITOR_LOGS = """
# Watch logs in real-time
tail -f trading_system.log

# Or on Windows:
Get-Content trading_system.log -Wait
"""

MONITOR_SIGNALS = """
# Check latest signal file
ls -la signals/signal_*.json | head -1

# View contents
cat signals/signal_*.json | tail -1 | python -m json.tool
"""

MONITOR_API_USAGE = """
# Count API calls (rough estimate)
grep -c "OpenAI API" trading_system.log
"""

# ============================================================================
# DEBUGGING COMMANDS
# ============================================================================

DEBUG_SYNTAX = """
# Check all Python files for syntax errors
python -m py_compile main.py
python -m py_compile analysis/*.py
python -m py_compile agents/*.py
python -m py_compile utils/*.py
python -m py_compile streamlit_app.py
"""

DEBUG_IMPORTS = """
# Check if all required packages are installed
python -c "
import crewai
import yfinance
import pandas_ta
import streamlit
import requests
import schedule
print('✅ All imports successful')
"
"""

DEBUG_CONFIG = """
# Verify config file loads correctly
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
"""

DEBUG_ENV = """
# Check if .env variables are loaded
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'OpenAI Key: {\"***\" + os.getenv(\"OPENAI_API_KEY\")[-4:] if os.getenv(\"OPENAI_API_KEY\") else \"NOT SET\"}'  )
print(f'NewsAPI Key: {\"***\" + os.getenv(\"NEWSAPI_KEY\")[-4:] if os.getenv(\"NEWSAPI_KEY\") else \"NOT SET\"}')
"
"""

# ============================================================================
# TESTING COMMANDS
# ============================================================================

TEST_YFINANCE = """
# Download sample data
python -c "
import yfinance as yf
data = yf.download('ORCL', period='1y')
print(f'Downloaded {len(data)} rows for ORCL')
print(data.head())
"
"""

TEST_NEWSAPI = """
# Test News API (requires NEWSAPI_KEY in .env)
python -c "
from analysis.sentiment import SentimentAnalyzer
sa = SentimentAnalyzer()
headlines = sa.get_top_headlines('ORCL', limit=3)
for h in headlines:
    print(f'Score: {h[\"score\"]:.2f} | {h[\"title\"]}')
"
"""

TEST_INDICATORS = """
# Test technical indicators
python -c "
from analysis.indicators import IndicatorCalculator
calc = IndicatorCalculator()
ind = calc.calculate_all_indicators('ORCL')
print(f'RSI: {ind[\"rsi\"]:.2f}')
print(f'ATR: {ind[\"atr\"]:.2f}')
print(f'MACD Cross: {ind[\"macd_cross\"]}')
print(f'Price > 200SMA: {ind[\"above_200sma\"]}')
"
"""

# ============================================================================
# MAINTENANCE COMMANDS
# ============================================================================

MAINT_BACKUP_SIGNALS = """
# Backup all signal files
cp -r signals signals_backup_$(date +%Y%m%d)

# Or on Windows:
Copy-Item -Path signals -Destination signals_backup_$(Get-Date -Format "yyyyMMdd") -Recurse
"""

MAINT_CLEANUP_LOGS = """
# Archive old logs
gzip trading_system.log
mv trading_system.log.gz logs_archive/

# Or on Windows:
Move-Item trading_system.log archive_$(Get-Date -Format "yyyyMMddHHmmss").log
"""

MAINT_UPDATE_DEPS = """
# Check for outdated packages
pip list --outdated

# Update all packages
pip install --upgrade -r requirements.txt
"""

# ============================================================================
# DEPLOYMENT COMMANDS
# ============================================================================

DEPLOY_DOCKER = """
# Build image
docker build -t trading-signals .

# Run container
docker run -e OPENAI_API_KEY=$YOUR_KEY -e NEWSAPI_KEY=$YOUR_KEY -p 8501:8501 trading-signals
"""

DEPLOY_AWS = """
# Install on EC2 Ubuntu
sudo apt update
sudo apt install python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure systemd service
sudo nano /etc/systemd/system/trading-signals.service
# [Unit]
# Description=Trading Signals Streamlit App
# [Service]
# User=ubuntu
# WorkingDirectory=/home/ubuntu/trading_system
# ExecStart=/home/ubuntu/venv/bin/streamlit run streamlit_app.py
# Restart=always
# [Install]
# WantedBy=multi-user.target

sudo systemctl enable trading-signals
sudo systemctl start trading-signals
"""

DEPLOY_STREAMLIT_CLOUD = """
# 1. Push to GitHub
git add .
git commit -m "Add trading system"
git push

# 2. Go to https://streamlit.io/cloud
# 3. Click "New app"
# 4. Select your repo and streamlit_app.py
# 5. Set secrets via Streamlit dashboard:
#    OPENAI_API_KEY = sk-...
#    NEWSAPI_KEY = ...
# 6. App deploys automatically!
"""

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

TUNE_REDUCE_TICKERS = """
# Edit config.yaml
# watchlist:
#   - ORCL
#   - NVDA
# (Keep only your preferred tickers for faster scans)
"""

TUNE_CACHE_SENTIMENT = """
# In sentiment.py, extend cache time:
# CACHE_MAX_AGE = 86400  # 24 hours instead of 30 minutes
"""

TUNE_PARALLEL_PROCESSING = """
# Not yet implemented, but future optimization:
# - Use ThreadPoolExecutor for concurrent ticker analysis
# - Process 5 tickers simultaneously instead of sequentially
# - Reduces scan time from 2-3 min to 45-60 seconds
"""

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║          TRADING SYSTEM COMMAND QUICK REFERENCE                 ║
    ╚══════════════════════════════════════════════════════════════════╝

    📋 QUICK START:
       1. pip install -r requirements.txt
       2. nano .env (add API keys)
       3. streamlit run streamlit_app.py
       4. Open http://localhost:8501

    🚀 COMMON WORKFLOWS:
       • WEB UI ONLY:  streamlit run streamlit_app.py
       • WITH SCHEDULER: python main.py (+ in another terminal)
       • SINGLE TICKER: Use web UI "Run Single Ticker" form

    🔍 MONITORING:
       • tail -f trading_system.log
       • ls -la signals/signal_*.json
       • Check web UI "View Results" tab

    ✅ TESTING:
       • python -m py_compile main.py
       • Check web UI runs without errors
       • Manual ticker scan to verify signals

    📚 DOCUMENTATION:
       • QUICK_REFERENCE.md  (this file)
       • README.md           (full docs)
       • QUICKSTART.md       (setup guide)
       • DEPLOYMENT.md       (deployment options)
       • config.yaml         (customization)

    🎯 For detailed commands, see the variables above.
    """)
