# 🤖 AI Traders - Intelligent Short CFD Recommendation System

An advanced multi-agent system powered by **CrewAI** that uses artificial intelligence to analyze news, stock market data, and technical patterns to recommend short CFD positions in the US market. The system brings together collaborative intelligence from 4 expert agents working in teams.

**Live Demo:** [Try on Streamlit Cloud]  
**Documentation:** [Full Docs]  
**Twitter:** [@AITradersBot]

---

## 🌟 Features

### 🧠 Multi-Agent Intelligence
- **News Researcher** (10 years US market experience) - Identifies market-moving events
- **News Manager** (20 years experience) - Synthesizes news into strategic insights
- **Stock Analyst** (10 years experience) - Technical & fundamental analysis
- **Portfolio Manager** (20 years experience) - Structures optimal short positions

### 💼 What It Does
✅ Analyzes breaking market news with sentiment analysis  
✅ Performs technical analysis to identify breakdown patterns  
✅ Evaluates fundamental deterioration  
✅ Recommends specific short CFD positions with entry/exit levels  
✅ Manages portfolio risk and position sizing  
✅ Provides real-time P&L monitoring  

### ⏰ Time Zone Features
🇺🇸 Displays US Eastern Time (ET) in AM/PM format  
🇪🇬 Shows Egyptian Time (CAT) in AM/PM format  
📅 Automatic timezone conversion  

### 🎯 Output
- Short CFD recommendations with confidence levels
- Entry prices and stop-loss levels
- Profit targets (multiple exit points)
- Risk/reward ratios
- Position sizing recommendations
- Portfolio allocation across sectors
- Real-time monitoring dashboard

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- OpenAI API Key (for LLM backbone)
- pip or conda

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ai-traders.git
cd ai-traders
```

2. **Create virtual environment**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup environment variables**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

5. **Run the Streamlit app**
```bash
streamlit run app.py
```

6. **Access the dashboard**
```
Open browser to: http://localhost:8501
```

---

## 📁 Project Structure

```
ai-traders/
├── app.py                 # Main Streamlit application
├── agents.py              # CrewAI agents and tasks setup
├── utils.py               # Utility functions (time handling, etc.)
├── requirements.txt       # Python dependencies
├── .env.example            # Example environment variables
├── .gitignore             # Git ignore file
├── README.md              # This file
├── Dockerfile             # Docker configuration
└── docs/
    ├── AGENTS.md          # Detailed agent descriptions
    ├── ARCHITECTURE.md    # System architecture
    └── API_INTEGRATION.md # API integration guide
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# Model Selection
OPENAI_MODEL_NAME=gpt-4

# Optional: Market Data APIs
ALPHA_VANTAGE_KEY=your_key
FINNHUB_API_KEY=your_key
NEWSAPI_KEY=your_key

# Application
DEMO_MODE=true
LOG_LEVEL=INFO
```

### Streamlit Configuration

Customize via sidebar:
- **Analysis Type**: Quick, Full Deep Dive, News Only, Technical Only
- **Sectors**: Filter by market sectors
- **Position Size**: Risk per trade
- **Leverage**: CFD leverage ratio (1-50x)
- **Stop Loss %**: Risk management level
- **Take Profit %**: Profit target levels

---

## 🎮 How to Use

### 1. **News Analysis Tab**
- View latest market-moving news
- See sentiment and affected sectors
- Identify potential short themes

### 2. **Stock Analysis Tab**
- Browse technical & fundamental scores
- Deep-dive into individual stocks
- Analyze charts and metrics

### 3. **Short Recommendations Tab**
- View top short CFD candidates
- Check entry/exit prices
- Review confidence levels and rationale

### 4. **Portfolio Strategy Tab**
- See sector allocation
- Understand risk management rules
- Review position sizing strategy

### 5. **Real-Time Monitoring Tab**
- Track active positions
- Monitor P&L
- Receive alerts

---

## 🧠 Agent Architecture

```
┌─────────────────────────────────────────────┐
│         CrewAI Orchestration Layer          │
└─────────────────────────────────────────────┘
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
   NEWS TEAM              STOCK TEAM
   ────────────          ────────────
   │                     │
   ├─ Researcher (10y)   ├─ Analyst (10y)
   │  • News analysis    │  • Technical analysis
   │  • Sentiment        │  • Fundamentals
   │  • Pattern finding  │  • Breakdowns
   │                     │
   └─ Manager (20y)      └─ Manager (20y)
      • Strategy           • Portfolio structure
      • Synthesis          • Risk management
      • Insights           • Position sizing
      │                    │
      └────────┬───────────┘
               ↓
        ┌──────────────────┐
        │  Recommendations │
        └──────────────────┘
```

---

## 📊 Supported Analysis

### News Analysis
- Economic indicators
- Earnings surprises
- Sector news
- Geopolitical events
- Fed policy changes

### Technical Analysis
- Breakdowns and support breaks
- Moving average analysis
- Divergences and momentum
- Pattern recognition
- Volume analysis

### Fundamental Analysis
- P/E ratio deterioration
- Cash flow concerns
- Debt levels
- Insider selling
- Short interest

### Risk Management
- Position sizing
- Stop loss placement
- Profit target selection
- Leverage management
- Portfolio correlation

---

## 🔗 API Integrations

### Currently Supported (Demo Mode)
- Placeholder API connections
- Sample data for testing

### Ready to Integrate
- **Alpha Vantage**: Stock & technical data
- **Finnhub**: News & company data
- **NewsAPI**: Real-time news
- **Yahoo Finance**: Historical data
- **Interactive Brokers**: Trading execution

---

## 🐳 Docker Deployment

### Build Docker Image
```bash
docker build -t ai-traders:latest .
```

### Run Container
```bash
docker run -e OPENAI_API_KEY=sk-xxx \
           -p 8501:8501 \
           ai-traders:latest
```

### Docker Compose
```bash
docker-compose up -d
```

---

## ☁️ Cloud Deployment

### Streamlit Cloud
1. Push to GitHub
2. Connect to Streamlit Cloud: https://streamlit.io/cloud
3. Deploy directly from repo
4. Add secrets in cloud settings

### AWS Deployment
```bash
# See docs/DEPLOYMENT.md for detailed AWS setup
```

### Google Cloud Run
```bash
# See docs/DEPLOYMENT.md for detailed GCP setup
```

---

## 📈 Performance Metrics

The system tracks:
- **Win Rate**: % of profitable trades
- **Risk/Reward Ratio**: Average profit vs risk
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough
- **Expectancy**: Average profit per trade

---

## 🔐 Security

- API keys handled via environment variables
- No credentials stored in code
- Rate limiting for API calls
- Input validation for all parameters
- Security headers for web deployment

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/AmazingFeature`
3. Commit changes: `git commit -m 'Add AmazingFeature'`
4. Push branch: `git push origin feature/AmazingFeature`
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**IMPORTANT:** This system is for educational and research purposes only. It is not financial advice.

- Past performance does not guarantee future results
- Short selling involves significant risks
- Use with proper risk management
- Trade only with capital you can afford to lose
- Consult a financial advisor before trading

---

## 🔗 Links & Resources

- **CrewAI Documentation**: https://crewai.io
- **Streamlit Documentation**: https://streamlit.io
- **OpenAI API**: https://openai.com/api
- **Stock Market Data**: https://www.alphavantage.co

---

## 📧 Contact & Support

- **Email**: support@aitraders.dev
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Twitter**: @AITradersBot

---

## 🙏 Acknowledgments

Built with:
- [CrewAI](https://crewai.io) - Multi-agent framework
- [Streamlit](https://streamlit.io) - Web interface
- [OpenAI](https://openai.com) - LLM backbone
- [Python](https://python.org) - Programming language

---

**Star ⭐ this repo if you find it useful!**

Last Updated: April 2026
