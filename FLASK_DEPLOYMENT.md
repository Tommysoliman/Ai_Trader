# 🚀 Flask API Deployment Guide

This is a **Flask REST API** version of the AI Traders system. Same functionality as Streamlit but easier to deploy anywhere!

## 📁 Structure

```
api/
├── main.py           # Flask app with all routes
templates/
├── index.html        # Single-page web app
requirements-api.txt  # Dependencies for Flask
railway.json          # Railway deployment config
Procfile              # Heroku/Railway deployment
```

## 🏃 Local Development

```bash
# 1. Install dependencies
pip install -r requirements-api.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Run Flask app
python api/main.py

# 4. Open browser
http://localhost:8000
```

## 🌐 Deploy to Railway (EASIEST - 5 MINUTES)

### Step 1: Sign up
1. Go to **https://railway.app/**
2. Sign in with GitHub

### Step 2: Deploy
1. Click **New Project**
2. Click **Deploy from GitHub repo**
3. Select `Tommysoliman/Ai_Trader`
4. Railway auto-detects Procfile
5. Click **Deploy**

### Step 3: Add Environment Variables
1. Go to your deployed project → **Variables**
2. Add these:
```
OPENAI_API_KEY=sk-proj-YOUR_KEY
OPENAI_MODEL_NAME=gpt-4
NEWSDATA_API_KEY=pub_YOUR_KEY
NEWSAPI_KEY=YOUR_KEY
```

### Step 4: Done!
Your app is live at: `https://your-project-name.railway.app/`

---

## 🟦 Deploy to Render

### Step 1: Create Render account
1. Go to **https://render.com/**
2. Sign in with GitHub

### Step 2: Deploy
1. Click **New** → **Web Service**
2. Select your GitHub repo
3. Fill in:
   - **Name:** `ai-traders`
   - **Runtime:** `Python 3.10`
   - **Build command:** `pip install -r requirements-api.txt`
   - **Start command:** `gunicorn -w 4 -b 0.0.0.0:$PORT api.main:app`
4. Click **Create Web Service**

### Step 3: Environment Variables
1. Go to **Environment**
2. Add same variables as Railway

### Step 4: Done!
Your app is live at: `https://ai-traders.onrender.com/`

---

## 🟩 Deploy to Heroku (Paid after free tier)

```bash
# 1. Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# 2. Login
heroku login

# 3. Create app
heroku create ai-traders

# 4. Set environment variables
heroku config:set OPENAI_API_KEY=sk-proj-YOUR_KEY

# 5. Deploy
git push heroku main

# 6. View logs
heroku logs --tail
```

---

## 📱 API Endpoints

### Health Check
- `GET /health` - Check if API is running

### Tab 1: Analyze Stock
- `GET /api/industries` - Get list of industries
- `GET /api/stocks/<industry>` - Get stocks in industry
- `POST /api/analyze-stock` - Analyze single stock
  ```json
  {"ticker": "AAPL"}
  ```

### Tab 2: Daily Scan
- `POST /api/daily-scan` - Scan multiple stocks
  ```json
  {"tickers": ["AAPL", "MSFT", "TSLA"]}
  ```

### Tab 3: Results
- `GET /api/results` - Get stored scan results
- `GET /api/export-excel` - Export results to Excel

### Tab 4: Q&A
- `POST /api/qa` - Ask market question
  ```json
  {"question": "What's the sentiment on tech stocks?"}
  ```
- `POST /api/stock-qa` - Ask about specific stock
  ```json
  {"ticker": "AAPL", "question": "Why is it up today?"}
  ```

### Tab 5: Framework
- `GET /api/framework` - Get 3-pillar framework info

---

## ⚙️ Configuration

All config in:
- `trading_system/config.yaml` - Stock watchlist, industries, thresholds
- `.env` - API keys and secrets

---

## 🔒 Security Notes

- ✅ `.env` in `.gitignore` - API keys not committed
- ✅ `requirements-api.txt` pinned versions for stability
- ✅ CORS enabled for mobile/web access
- ✅ Error handling for all endpoints

---

## 📊 Performance

- **Local:** ~2-3 sec per stock
- **Cloud:** ~3-5 sec per stock (varies by region)
- **Parallel scan:** 5 stocks simultaneously

---

## 🐛 Troubleshooting

### Port already in use locally
```bash
# Change port in api/main.py (last line)
# Or kill process using 8000
lsof -ti:8000 | xargs kill -9
```

### ModuleNotFoundError on deployment
- Check `requirements-api.txt` has all dependencies
- Ensure `/trading_system` exists in repo

### API keys not working
- Verify they're set in deployment platform (not in `.env`)
- Test locally first with `.env`

---

## 📈 Next Steps

1. Deploy to Railway (easiest)
2. Add authentication if needed
3. Create mobile app (React Native / Flutter)
4. Add database for historical results
5. Add webhook notifications

---

**Status:** ✅ Ready to deploy!  
**Latest:** Flask API fully functional with all 5 tabs
