# System Architecture

## Overview

AI Traders uses a sophisticated multi-agent orchestration system powered by CrewAI to analyze both news and market data to generate short CFD recommendations.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│  - Dashboard with 5 main tabs                              │
│  - Real-time time zone display (US & Egypt)                │
│  - Interactive configuration                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  - agents.py: CrewAI orchestration                          │
│  - app.py: Streamlit UI logic                              │
│  - utils.py: Helper functions                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
    ┌───────┐    ┌────────┐    ┌──────────┐
    │News   │    │Stock   │    │Portfolio │
    │Team   │    │Team    │    │Manager   │
    └───────┘    └────────┘    └──────────┘
        │             │             │
        ↓             ↓             ↓
    [LLM]         [LLM]         [LLM]
```

## Agent Components

### 1. News Researcher (10 years)
**Role**: Research and sentiment analysis
- Reads latest market news
- Analyzes sentiment and impact
- Identifies bearish themes
- Connects news to sectors

**Tools**:
- News Database Search
- Sentiment Analysis
- Economic Calendar Parser
- News Aggregator

### 2. News Manager (20 years)
**Role**: Strategic synthesis and insights
- Reviews news research
- Synthesizes into trading themes
- Identifies affected stocks/sectors
- Creates short theses

**Tools**:
- News Analysis Tools
- Sector Correlations
- Historical Context Analyzer
- Theme Synthesizer

### 3. Stock Market Analyst (10 years)
**Role**: Technical and fundamental analysis
- Screens for technical breakdowns
- Evaluates fundamental deterioration
- Identifies support breaks
- Builds shortable stock list

**Tools**:
- Price Data Fetcher
- Technical Indicator Calculator
- Fundamental Data Reader
- Pattern Recognition Engine

### 4. Portfolio Manager (20 years)
**Role**: Position structuring and risk management
- Reviews stock recommendations
- Sizes positions appropriately
- Sets stops and targets
- Manages portfolio correlation

**Tools**:
- Position Sizer
- Risk Calculator
- Leverage Optimizer
- Portfolio Analyzer

## Data Flow

```
1. User Input
   ├─ Select sectors
   ├─ Set risk parameters
   ├─ Choose analysis type
   └─ Click "Run Analysis"
          ↓
2. Crew Initialization
   ├─ Create agent instances
   ├─ Load tools
   └─ Set tasks
          ↓
3. News Analysis Pipeline
   ├─ News Researcher gets latest news
   ├─ News Manager synthesizes insights
   └─ Output: Trading themes & sectors
          ↓
4. Stock Analysis Pipeline
   ├─ Stock Analyst screens stocks
   ├─ Portfolio Manager evaluates
   └─ Output: Top short candidates
          ↓
5. Integration
   ├─ Combine news & stock insights
   ├─ Generate recommendations
   └─ Calculate risk metrics
          ↓
6. Display Results
   ├─ Show recommendations in UI
   ├─ Display P&L projections
   └─ Update monitoring dashboard
```

## Task Execution Flow

```
Task 1: News Research
├─ Agent: News Researcher
├─ Goal: Analyze market-moving news
└─ Output: News analysis & sentiment

Task 2: News Strategy
├─ Agent: News Manager
├─ Goal: Synthesize into trading themes
└─ Output: Sector & theme insights

Task 3: Stock Analysis
├─ Agent: Stock Analyst
├─ Goal: Identify short candidates
└─ Output: Technical & fundamental analysis

Task 4: Portfolio Strategy
├─ Agent: Portfolio Manager
├─ Goal: Structure positions
└─ Output: Final recommendations with entry/exit
```

## Key Features

### 1. Time Zone Handling
- **Location**: `utils.py`
- **Functionality**:
  - US Eastern Time (ET) in 12-hour AM/PM format
  - Egyptian Time (CAT) in 12-hour AM/PM format
  - Automatic current time display
  - Separate date display for each timezone

### 2. Risk Management
- Position sizing based on account size
- Stop loss calculation
- Profit target tiers
- Leverage management
- Portfolio correlation analysis

### 3. Multi-Agent Collaboration
- News team provides market context
- Stock team provides stock-specific analysis
- Portfolio manager integrates both
- Shared memory across agents
- Delegation capabilities

### 4. Real-Time Monitoring
- Active position tracking
- P&L monitoring
- Alert system
- Performance metrics
- Trade history

## Tool Integrations

### Current (Demo Mode)
```python
@tool("News Database")
def search_market_news(query: str) -> str:
    # Placeholder for news API integration
    
@tool("Stock Data")
def get_stock_data(ticker: str) -> str:
    # Placeholder for stock data API integration
    
@tool("Market Sentiment")
def analyze_sentiment() -> str:
    # Placeholder for sentiment analysis
    
@tool("CFD Analysis")
def cfd_recommendation(ticker: str) -> str:
    # Placeholder for CFD analysis
```

### Future Integrations
- Alpha Vantage API (stock data)
- Finnhub API (news & company data)
- NewsAPI (news aggregation)
- IB API (live trading)
- Polygon.io (market data)

## Configuration Management

```python
# Environment Variables (.env)
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL_NAME = "gpt-4"
ALPHA_VANTAGE_KEY = "..."
DEMO_MODE = true

# Streamlit Config (sidebar)
analysis_type: Selection
market_focus: Multi-select
position_size: Slider
leverage: Slider
stop_loss_pct: Slider
take_profit_pct: Slider
```

## Deployment Architecture

### Local Development
```
┌──────────┐
│  Streamlit
│  Dev Server
│  :8501
└──────────┘
    ↑
    │
    ↓
┌──────────┐
│  CrewAI
│  Agents
└──────────┘
    ↑
    │
    ↓
┌──────────┐
│  .env
│  Config
└──────────┘
```

### Docker Deployment
```
┌────────────────────┐
│   Docker Container │
│  ┌──────────────┐  │
│  │  Streamlit   │  │
│  │  CrewAI      │  │
│  │  Python App  │  │
│  └──────────────┘  │
└────────────────────┘
     Port 8501
```

### Cloud Deployment (Streamlit Cloud)
```
┌─────────────────┐
│  Streamlit Cloud│
│  ┌───────────┐  │
│  │ AI Traders│  │
│  └───────────┘  │
└─────────────────┘
```

## Performance Considerations

### Scalability
- Agent parallelization
- Task queuing
- Caching mechanisms
- Rate limiting

### Latency
- News analysis: 5-10 seconds
- Stock analysis: 10-15 seconds
- Portfolio synthesis: 3-5 seconds
- Total pipeline: ~20-30 seconds

### Resource Usage
- Memory: ~500MB base + API callouts
- CPU: Minimal except during analysis
- API calls: Dependent on configuration
- Storage: Local cache for historical data

## Security Architecture

```
┌─────────────────────────────────────┐
│        API Keys in Environment       │
│  (Never hardcoded in source code)    │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│        Application Layer            │
│  (Secure API communication)         │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│        Data Processing              │
│  (Input validation & sanitization)  │
└─────────────────────────────────────┘
```

## Error Handling

- API failure fallbacks
- User input validation
- Agent error recovery
- Retry mechanisms
- Logging & monitoring

## Future Enhancements

1. **Real Data Integration**
   - Live market data feeds
   - Real-time news streaming
   - Order execution

2. **Advanced Analytics**
   - Machine learning models
   - Backtesting engine
   - Strategy optimization

3. **Multi-User Features**
   - User authentication
   - Portfolio persistence
   - Shared analysis workspace

4. **Extended Coverage**
   - International markets
   - Crypto markets
   - Options strategies
