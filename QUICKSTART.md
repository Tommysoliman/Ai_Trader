# Quick Start Guide

Get AI Traders running in 5 minutes!

## Option 1: Local Installation (Recommended for Development)

### Prerequisites
- Windows, macOS, or Linux
- Python 3.10 or higher
- pip (Python package manager)
- OpenAI API key (free trial available)

### Step-by-Step

#### 1. Clone/Download Repository
```bash
git clone https://github.com/yourusername/ai-traders.git
cd ai-traders
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Setup Environment
```bash
# Copy example to actual .env file
cp .env.example .env

# Edit .env file and add your OpenAI API key
# On Windows: notepad .env
# On macOS/Linux: nano .env
```

Edit `.env` to add:
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

#### 5. Run Application
```bash
streamlit run app.py
```

#### 6. Open in Browser
Navigate to `http://localhost:8501`

---

## Option 2: Docker (Recommended for Production)

### Prerequisites
- Docker installed (https://www.docker.com/products/docker-desktop)

### Step-by-Step

#### 1. Clone Repository
```bash
git clone https://github.com/yourusername/ai-traders.git
cd ai-traders
```

#### 2. Build Docker Image
```bash
docker build -t ai-traders:latest .
```

#### 3. Run Container
```bash
docker run -e OPENAI_API_KEY=sk-your-key-here \
           -p 8501:8501 \
           ai-traders:latest
```

#### 4. Open in Browser
Navigate to `http://localhost:8501`

### Docker Compose Alternative
```bash
# Set your API key in .env
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# Start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

---

## Option 3: Streamlit Cloud (Easiest)

### Prerequisites
- GitHub account
- Streamlit Cloud account (free at https://streamlit.io/cloud)

### Step-by-Step

#### 1. Push to GitHub
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

#### 2. Deploy on Streamlit Cloud
- Go to https://streamlit.io/cloud
- Sign in with GitHub
- Click "New app"
- Select your repository: `ai-traders`
- Select branch: `main`
- Set main file path: `app.py`
- Click "Deploy"

#### 3. Add Secrets
- In your Streamlit Cloud dashboard
- Click on your app settings
- Go to "Secrets"
- Add: `OPENAI_API_KEY = sk-your-actual-key`

#### 4. Access App
Your app is now live! Share the URL with others.

---

## Getting Your OpenAI API Key

1. Visit https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (you won't see it again!)
5. Paste into `.env` file

**Cost**: First $5 free credit, then pay-as-you-go

---

## First Time Setup Walkthrough

### 1. Dashboard Welcome
You'll see the main dashboard with the AI Traders logo and current time displays showing:
- 🇺🇸 US Eastern Time (AM/PM)
- 🇪🇬 Egyptian Time (AM/PM)

### 2. Sidebar Configuration
On the left sidebar, you'll see controls:

**Analysis Type:**
- Quick Analysis (2-3 minutes)
- Full Deep Dive (5-10 minutes)
- News Only
- Technical Only

**Market Focus:**
- Select sectors you want to analyze
- Default: All Sectors

**Position Sizing:**
- Set risk amount per trade
- Default: $5,000

**Settings:**
- Toggle CFD Leverage
- Set leverage ratio
- Set stop loss %
- Set take profit %

### 3. Run Your First Analysis
1. Keep default settings for demo
2. Click blue "Run Analysis" button
3. Watch the analysis progress
4. Results appear in tabs below

### 4. Explore the Tabs

**📰 News Analysis**
- Latest market news
- Sentiment analysis
- Affected sectors

**📊 Stock Analysis**
- Stock screening results
- Technical scores
- Individual deep dives

**💰 Short Recommendations**
- Top short CFD candidates
- Entry/exit points
- Risk/reward ratios

**📈 Portfolio Strategy**
- Sector allocation
- Risk management rules
- Position sizing strategy

**⚡ Real-Time Monitoring**
- Active positions
- P&L tracking
- Performance alerts

---

## Common Issues & Solutions

### "ModuleNotFoundError: No module named 'streamlit'"

```bash
# Make sure virtual environment is activated
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Then install requirements
pip install -r requirements.txt
```

### "OPENAI_API_KEY not found"

```bash
# Check .env file exists in project root
# Check OPENAI_API_KEY is in .env with your real key
# Restart streamlit app

streamlit run app.py
```

### "Port 8501 already in use"

```bash
# Use different port
streamlit run app.py --server.port=8502
```

### "Docker: command not found"

- Install Docker Desktop: https://www.docker.com/products/docker-desktop
- Restart terminal/command prompt after installation

---

## Next Steps

### 1. Integrate Real APIs (Optional)
- Add Alpha Vantage for stock data
- Add Finnhub for news
- See `docs/API_INTEGRATION.md` for details

### 2. Customize Configuration
- Modify agent prompts in `agents.py`
- Adjust Streamlit layout in `app.py`
- Add more technical indicators

### 3. Deploy Professionally
- Use Streamlit Cloud for easy hosting
- Or deploy on AWS/GCP/Azure
- See `docs/DEPLOYMENT.md` for details

### 4. Add Real Trading
- Integrate Interactive Brokers API
- Add position execution
- Real money trading (with extreme caution!)

---

## File Structure Reference

```
ai-traders/
├── app.py                 ← Main app (run this)
├── agents.py              ← CrewAI agents
├── utils.py               ← Helper functions
├── requirements.txt       ← Python packages
├── .env.example           ← Config template
├── .env                   ← Your config (create this)
├── .gitignore             ← Git ignore rules
├── Dockerfile             ← Docker config
├── docker-compose.yml     ← Docker Compose config
├── README.md              ← Full documentation
├── LICENSE                ← MIT License
├── QUICKSTART.md          ← This file!
└── docs/
    ├── ARCHITECTURE.md    ← System design
    ├── AGENTS.md          ← Agent details
    ├── API_INTEGRATION.md ← API setup
    └── DEPLOYMENT.md      ← Production deployment
```

---

## Real-World Usage

### Daily Workflow
1. Open dashboard in morning (9:30 AM ET market open)
2. Sidebar: Select sectors of interest
3. Click "Run Analysis"
4. Review recommendations
5. Monitor P&L in real-time tab
6. Adjust stops as needed

### Weekly Review
- Check performance metrics
- Analyze winning vs losing trades
- Adjust leverage/position sizing
- Update sector focus

### Monthly Review
- Full portfolio analysis
- Risk metrics review
- Strategy optimization
- Budget allocation

---

## Getting Help

### Documentation
- Full docs: `README.md`
- Architecture: `docs/ARCHITECTURE.md`
- Agents: `docs/AGENTS.md`
- API setup: `docs/API_INTEGRATION.md`

### Community
- GitHub Issues: Report bugs
- GitHub Discussions: Ask questions
- Twitter: @AITradersBot

### Support
- Email: support@aitraders.dev
- Response time: 24-48 hours

---

## Pro Tips 🎯

1. **Start with demo mode** - Don't change defaults right away
2. **Read agent profiles** - Understand what each agent does
3. **Use small positions** - Start with $500-$1000 position size
4. **Monitor carefully** - Don't set and forget positions
5. **Keep leverage low** - Start with 2-3x, scale up with experience
6. **Use stop losses** - Always protect your downside
7. **Review results** - Learn from each trade
8. **Follow money management** - Risk only 1-2% per trade

---

## Keyboard Shortcuts

- `Ctrl+C` (or `Cmd+C`) - Stop running app
- ↓ and ↑ arrows - Adjust sidebar sliders
- `Shift+Click` - Multi-select sectors
- `R` - Refresh data

---

## Performance Expectations

- Dashboard loads: ~2 seconds
- Analysis runs: ~20-30 seconds
- Recommendations display: ~1 second
- Real-time monitoring: Updates every 5 seconds

---

## Security Best Practices

✅ DO:
- Keep API keys in `.env` (not in code)
- Use `.gitignore` to prevent committing secrets
- Rotate API keys regularly
- Use environment variables in production

❌ DON'T:
- Commit `.env` to GitHub
- Share API keys with others
- Use same keys for development and production
- Hardcode secrets in code

---

## Ready to Start?

```bash
# Copy this command and run in your terminal:
git clone https://github.com/yourusername/ai-traders.git && cd ai-traders && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cp .env.example .env && echo "Done! Edit .env with your OpenAI API key, then run: streamlit run app.py"
```

**Questions?** See the full README.md for more details!

---

Happy Trading! 🚀
