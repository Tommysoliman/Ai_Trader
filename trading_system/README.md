# CFD Trading Signal System

A Python-based CFD trading signal generation system using CrewAI, yfinance, and technical analysis.

## Overview

**Architecture:**
- **Daily Run**: 08:00 Cairo time (UTC+2) - Full signal scan on watchlist
- **Hourly Run**: Every hour when active signals exist - Entry point monitoring
- **LLM**: CrewAI orchestrates 4 agents; all math done in Python
- **Output**: Structured JSON trade cards with risk management parameters

## Quick Start

### 1. Installation

```bash
cd trading_system
pip install -r requirements.txt
```

### 2. Configuration

Edit `.env` with your API keys:
```env
OPENAI_API_KEY=your_key_here
NEWSAPI_KEY=your_key_here
```

Edit `config.yaml` to customize:
- **Watchlist**: Add/remove tickers (10 by default)
- **Thresholds**: RSI, MACD, sentiment levels
- **Leverage caps**: MiFID II compliance settings
- **Scheduler**: Daily run time (default 08:00 Cairo)

### 3. Run the System

```bash
python main.py
```

System will:
- Schedule daily 08:00 Cairo scan
- Monitor for hourly entry opportunities
- Output JSON trade cards to `signals/signal_YYYYMMDD.json`
- Print trade card summaries to terminal

## File Structure

```
trading_system/
├── main.py                  # Scheduler + entry point
├── config.yaml              # Watchlist, thresholds, leverage
├── requirements.txt         # Python dependencies
├── .env                     # API keys
│
├── signals/                 # Output directory
│   └── signal_20240120.json # Daily trade cards
│
├── agents/
│   ├── agents.py            # 4 agent definitions
│   ├── tasks.py             # 4 task definitions
│   ├── crew.py              # Crew orchestration
│   └── __init__.py
│
├── analysis/
│   ├── indicators.py        # Technical calculations (pandas_ta)
│   ├── sentiment.py         # Keyword-based news scoring
│   ├── earnings.py          # Earnings calendar check
│   └── __init__.py
│
└── utils/
    ├── trade_card.py        # Trade card builder + JSON writer
    └── __init__.py
```

## Signal Generation Flow

### Python Layer (No LLM)
1. **Download OHLCV data** (yfinance, daily + hourly)
2. **Calculate indicators** (pandas_ta):
   - RSI(14)
   - MACD(12,26,9)
   - ATR(14)
   - 200-day SMA
   - 50-day SMA
3. **Fetch headlines** (NewsAPI, last 24h)
4. **Score sentiment** (keyword-based, -1.0 to +1.0)
5. **Check earnings** (skip if within 3 days)

### CrewAI Pipeline (LLM-Driven)

**Task 1: Research** → News Researcher
- Input: Headlines + sentiment score
- Output: Identified catalyst, type, thesis

**Task 2: Synthesis** → News Manager
- Input: Research output + technical context
- Output: Confidence score (0-100)
- **GATE**: If confidence < 65 → HOLD, STOP

**Task 3: Validation** → Stock Analyst
- Input: Synthesis + technical indicators
- Output: PASS or FAIL
- **GATE**: If FAIL → HOLD, STOP

**Task 4: Portfolio** → Portfolio Manager
- Input: PASS validation + all data
- Output: **Complete Trade Card (JSON)**

## Bullish Signal Conditions
ALL must be true:
- RSI(14) < 45
- MACD line crossed above signal line (last 3 candles)
- Price above 200 SMA
- Sentiment score > 0.2

## Bearish Signal Conditions
ALL must be true:
- RSI(14) > 58
- MACD line crossed below signal line (last 3 candles)
- Price below 200 SMA
- Sentiment score < -0.2

## Trade Card Structure

```json
{
  "ticker": "ORCL",
  "signal": "BUY",
  "entry_zone_low": 125.50,
  "entry_zone_high": 126.80,
  "entry_price": 126.15,
  "stop_loss": 123.45,
  "stop_loss_method": "1.5x ATR (1.70) from entry",
  "take_profit_1": 128.85,
  "take_profit_2": 131.55,
  "rr_ratio_tp1": 1.67,
  "rr_ratio_tp2": 3.33,
  "leverage_recommended": 5,
  "leverage_max_mifid2": 5,
  "timeframe": "swing_3_7_days",
  "confidence": 78,
  "catalyst": "Earnings beat + Oracle Cloud growth acceleration",
  "sentiment_score": 0.45,
  "rsi": 42.5,
  "macd_cross": "bullish",
  "above_200sma": true,
  "skip_reason": null,
  "run_timestamp": "2024-01-20T08:00:00Z"
}
```

## Risk Management

### Entry Zone
- **BUY**: low = current price, high = current + 0.5*ATR
- **SELL**: low = current - 0.5*ATR, high = current price

### Stop Loss (ATR-Based)
- **BUY SL**: entry - 1.5*ATR
- **SELL SL**: entry + 1.5*ATR

### Take Profits
- **TP1**: entry ± 2.0*ATR (Risk/Reward = 1:1.33)
- **TP2**: entry ± 4.0*ATR (Risk/Reward = 1:2.67)

### MiFID II Leverage Compliance
| Asset Class | Max Leverage |
|------------|-------------|
| Stocks     | 5:1        |
| Commodities| 10:1       |
| Crypto     | 2:1        |

**Portfolio Manager enforces these caps and CANNOT override them.**

## Sentiment Scoring

### Positive Keywords
upgrade, beat, growth, partnership, bullish, strong, raised, buyback, outperform, gain, surge, recovery, momentum, positive, approval, deal, contract, expansion, record, profit

### Negative Keywords
downgrade, miss, layoff, investigation, bearish, weak, cut, lawsuit, underperform, loss, decline, concern, selloff, negative, warning, fraud, risk, delay, recall, bankruptcy

**Algorithm:**
- Count keywords in each headline
- Net score = (positive_count - negative_count) / total_keywords
- Normalize to -1.0 to +1.0 range
- Aggregate across all headlines

## Hourly Entry Monitor

After daily run:
1. Stores all BUY/SELL signals with entry zones
2. Every hour, checks if current price is within entry zone
3. If yes: prints **ENTRY ALERT** to terminal
4. Shows current price vs. entry zone

Example output:
```
🎯 ENTRY ALERT: NVDA BUY
   Current Price: $875.25
   Entry Zone: $873.00 - $876.50
   ✅ PRICE IN ENTRY ZONE - READY FOR EXECUTION
```

## Error Handling

- **No yfinance data**: Skip ticker, log warning, continue
- **NewsAPI error**: Set sentiment to 0.0, proceed
- **CrewAI failure**: Return HOLD card with skip_reason="AGENT_ERROR"
- **Earnings check error**: Skip conservatively, flag as SKIP_EARNINGS
- **Any ticker failure**: Never crashes full run, continues to next ticker

## Output Files

### Log File
`trading_system.log` - Complete execution log with timestamps

### Trade Cards
`signals/signal_YYYYMMDD.json`

Structure:
```json
{
  "run_timestamp": "2024-01-20T08:00:00Z",
  "total_signals": 10,
  "buy_signals": 3,
  "sell_signals": 1,
  "hold_signals": 6,
  "trade_cards": [...]
}
```

## Customization

### Add More Tickers
Edit `config.yaml`:
```yaml
watchlist:
  - ORCL
  - NVDA
  - MYNEWTICKER
```

### Adjust RSI Thresholds
Edit `config.yaml`:
```yaml
indicators:
  rsi_bullish_threshold: 40  # Lower = more aggressive
  rsi_bearish_threshold: 65  # Higher = more aggressive
```

### Change Daily Run Time
Edit `config.yaml`:
```yaml
scheduler:
  daily_run_time: "16:00"  # 4 PM Cairo time
```

### Adjust Confidence Gate
Edit `config.yaml`:
```yaml
crewai:
  min_confidence_to_validate: 70  # Stricter than default 65
```

## API Requirements

1. **OpenAI API** (CrewAI backbone)
   - Used for all agent reasoning
   - Estimated cost: ~$0.10-0.50 per daily run (10 tickers)

2. **NewsAPI Free Tier**
   - 100 requests/day
   - Sufficient for daily + hourly runs on 10 tickers

3. **yfinance** (Free)
   - No API key required
   - Rate limit: ~2000 requests/day (no problem)

## Performance

- **Daily full scan**: ~2-3 minutes (10 tickers)
  - 30% time: yfinance downloads
  - 50% time: CrewAI agents
  - 20% time: NewsAPI queries
- **Hourly entry check**: ~10-20 seconds
- **Memory usage**: ~200-300 MB

## Advanced Usage

### Run Backtest on Specific Ticker
```python
from analysis.indicators import IndicatorCalculator
from analysis.sentiment import SentimentAnalyzer

calc = IndicatorCalculator(config)
sentiment = SentimentAnalyzer(config)

data = calc.calculate_all_indicators('ORCL')
score = sentiment.calculate_sentiment_score('ORCL')
```

### Manually Trigger Daily Run
```python
from main import CFDTradingSystem

system = CFDTradingSystem()
trade_cards = system.daily_run()
```

## Troubleshooting

**Q: "No data found for TICKER"**
- A: Ticker doesn't exist or yfinance rate limit. Check ticker spelling.

**Q: "NewsAPI error"**
- A: Check API key in .env, verify endpoint status, check rate limits.

**Q: "CrewAI timeout"**
- A: Reduce complexity in task prompts or switch to faster LLM (Claude).

**Q: "JSON parse error in trade card"**
- A: Portfolio Manager output is malformed. Check LLM output quality.

## Support & Logging

All operations logged to `trading_system.log`. For detailed debugging:
```bash
tail -f trading_system.log
```

## License

Internal use only. Do not share API keys.

---

**Built with:**
- CrewAI v0.15+
- yfinance v0.2+
- pandas_ta v0.3+
- OpenAI API
- NewsAPI
