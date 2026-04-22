# Quick Start Guide

## Step 1: Install Dependencies

```bash
cd trading_system
pip install -r requirements.txt
```

## Step 2: Configure API Keys

Copy `.env` and add your keys:
```bash
cp .env .env.local
```

Edit `.env.local`:
```env
OPENAI_API_KEY=sk-your-key-here
NEWSAPI_KEY=your-newsapi-key-here
```

Get your keys:
- **OpenAI**: https://platform.openai.com/api-keys
- **NewsAPI**: https://newsapi.org/register

## Step 3: Verify Configuration

Review `config.yaml`:
- Watchlist has your tickers
- `daily_run_time: "08:00"` is your desired time (Cairo UTC+2)
- Thresholds match your strategy

## Step 4: Run the System

```bash
python main.py
```

**Expected output:**
```
🚀 Starting CFD Trading Signal System
   Watchlist: ORCL, NVDA, MSFT, TSLA, META, GLD, USO, SPY, QQQ, AAPL
   Config: /path/to/config.yaml

📅 Daily run scheduled for 08:00 Cairo time
📅 Hourly run scheduled every hour

⏰ Scheduler started. Waiting for scheduled times...
   Press Ctrl+C to stop
```

## Step 5: First Manual Run (Optional)

To test immediately without waiting for 08:00:

```python
from main import CFDTradingSystem

system = CFDTradingSystem()
trade_cards = system.daily_run()  # Run immediately
```

## Step 6: Monitor Output

### Terminal Output
- Real-time trade card printouts
- Entry alerts during hourly runs

### JSON Files
Check `signals/signal_20240120.json` (today's date) for all trade cards

### Log File
`trading_system.log` - Full execution history

## Example Trade Card Output

```
======================================================================
📊 TRADE CARD: ORCL
======================================================================
Signal: BUY
Confidence: 78/100
Catalyst: Earnings beat + Oracle Cloud growth

ENTRY ZONE
  Low:  $125.50
  High: $126.80

RISK MANAGEMENT
  Entry: $126.15
  Stop Loss: $123.45 (1.5x ATR (1.70) from entry)
  TP1: $128.85 (RR: 1:1.67)
  TP2: $131.55 (RR: 1:3.33)

LEVERAGE
  Recommended: 5:1
  MiFID II Max: 5:1

TECHNICALS
  RSI(14): 42.5
  MACD Cross: bullish
  Above 200 SMA: True

Timestamp: 2024-01-20T08:00:00Z
======================================================================
```

## Expected Behavior

**Daily Run (08:00 Cairo):**
1. Downloads OHLCV data for all tickers
2. Calculates technical indicators
3. Fetches last 24h news
4. Runs CrewAI pipeline (4 agents, ~2-3 min)
5. Outputs JSON trade cards
6. Stores active BUY/SELL signals

**Hourly Run (Every hour):**
- Only if active signals exist from daily run
- Checks if current price in entry zone
- Prints **ENTRY ALERT** if zone reached

## Stopping the System

```bash
Press Ctrl+C to stop the scheduler
```

## Troubleshooting First Run

**Issue:** "No module named 'crewai'"
**Solution:** Run `pip install -r requirements.txt` again

**Issue:** "OPENAI_API_KEY not found"
**Solution:** Check `.env` file is in `trading_system/` directory with correct key

**Issue:** "No data found for TICKER"
**Solution:** Verify ticker is valid (e.g., ORCL not ORC)

**Issue:** "CrewAI timeout after 60 seconds"
**Solution:** Normal - agents are thinking. Wait for completion.

## Next Steps

1. Let first daily run complete (watch the terminal)
2. Check `signals/signal_YYYYMMDD.json` for trade cards
3. Review confidence scores and risk metrics
4. Adjust thresholds in `config.yaml` if needed
5. Monitor next hourly run for entry alerts

---

**You're ready! System will run automatically at scheduled times.**
