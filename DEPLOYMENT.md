# 🚀 Deployment Guide - AI Traders

This guide explains how to deploy the AI Traders system to GitHub and Streamlit Cloud.

---

## 📦 GitHub Deployment (Completed)

The code is already pushed to GitHub at: **https://github.com/Tommysoliman/Ai_Trader**

**Latest Commit:** `614748c` - Tab reordering, widget keys, chatbot integration fix

### What's Tracked on GitHub:
✅ All source code (`trading_system/` directory)  
✅ Configuration files (`config.yaml`)  
✅ Requirements (`requirements.txt`, `requirements-cloud.txt`)  
✅ Streamlit configuration (`.streamlit/config.toml`)  
✅ Documentation (README.md, FIXES_APPLIED.md)  

### What's Ignored:
❌ `.env` - API keys and secrets (not committed for security)  
❌ `.venv/` - Virtual environment  
❌ `__pycache__/` - Python cache  
❌ Signal JSON files - Generated data  

---

## 🌐 Streamlit Cloud Deployment

### Step 1: Prepare Environment Variables

Before deploying to Streamlit Cloud, you need to set up secrets in the Streamlit Cloud dashboard:

1. Go to **https://share.streamlit.io/**
2. Sign in or create a Streamlit account
3. Click **New App** and select:
   - GitHub repository: `Tommysoliman/Ai_Trader`
   - Branch: `main`
   - Main file path: `streamlit_app.py`

### Step 2: Configure Secrets in Streamlit Cloud

After creating the app, configure these environment variables in the app settings:

**Secrets Management:**
1. Go to your deployed app → **Settings** → **Secrets**
2. Add the following variables:

```toml
# OpenAI Configuration
OPENAI_API_KEY = "sk-proj-YOUR_OPENAI_KEY_HERE"
OPENAI_MODEL_NAME = "gpt-4"

# Anthropic Configuration (Fallback LLM)
ANTHROPIC_API_KEY = "sk-ant-YOUR_ANTHROPIC_KEY_HERE"

# News API Configuration
NEWSDATA_API_KEY = "pub_YOUR_NEWSDATA_KEY_HERE"
NEWSAPI_KEY = "YOUR_NEWSAPI_KEY_HERE"

# Demo Mode
DEMO_MODE = "false"
LOG_LEVEL = "INFO"
```

### Step 3: Deploy

Once secrets are configured:

1. Streamlit Cloud will automatically detect changes pushed to GitHub
2. Click **Deploy** or wait for automatic redeploy (enabled by default)
3. Your app will be live at: `https://share.streamlit.io/Tommysoliman/Ai_Trader/main/streamlit_app.py`

---

## 📋 Deployment Checklist

- [x] Code pushed to GitHub (main branch)
- [x] `requirements.txt` updated with correct versions
- [x] `streamlit_app.py` at root level (wrapper that imports from `trading_system/`)
- [x] `.streamlit/config.toml` configured for dark theme
- [x] `.env` is in `.gitignore` (not committed)
- [ ] Streamlit account created
- [ ] GitHub repository connected to Streamlit Cloud
- [ ] Secrets configured in Streamlit Cloud dashboard
- [ ] App deployed and live

---

## 🔧 Local Development

To run locally during development:

```bash
# Activate virtual environment
cd "c:\Users\tommy\OneDrive\Desktop\Ai Traders"
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run streamlit_app.py
```

The app runs at: **http://localhost:8501**

---

## 🐛 Troubleshooting

### Issue: "Module not found" errors
- **Solution:** Ensure `requirements.txt` has all dependencies with correct versions
- Streamlit Cloud may take 1-2 minutes to install dependencies on first deploy

### Issue: API keys not working on Cloud
- **Solution:** Verify secrets are set in Streamlit Cloud dashboard (not `.env`)
- Check that `.env` is in `.gitignore` and was not committed

### Issue: App crashes after deployment
- **Solution:** Check Streamlit Cloud logs for errors
- Verify all required API keys are set in secrets
- Ensure `streamlit_app.py` is at the root level

---

## 📊 App Features on Streamlit Cloud

Once deployed, all features will be available:

1. **🔍 Analyze Stock** - Industry dropdown with 30+ stocks
2. **🚀 Daily Scan** - Parallel downloads of multiple stocks
3. **📊 Results** - Color-coded BUY/SELL/HOLD signals
4. **💬 News Q&A** - CrewAI chatbot with market intelligence
5. **📚 About** - 3-Pillar framework explanation

---

## 📈 Monitoring

### On Streamlit Cloud:
- View real-time logs in app dashboard
- Monitor app performance and usage
- Check memory and CPU usage
- Set up email notifications for crashes

### Locally:
- Run `streamlit run streamlit_app.py --logger.level=debug` for detailed logs
- Check `streamlit_error.log` for error history

---

## 🔄 Continuous Integration

**Current Setup:**
- GitHub branch: `main`
- Auto-deploy: Enabled (Streamlit Cloud redeploys on each push)
- Latest commit: `614748c`

**To Update After Changes:**
```bash
git add .
git commit -m "Your change description"
git push origin main
# Streamlit Cloud automatically redeploys
```

---

## 📞 Support

- **Repository:** https://github.com/Tommysoliman/Ai_Trader
- **Streamlit Docs:** https://docs.streamlit.io/
- **CrewAI Docs:** https://docs.crewai.io/

---

**Status:** ✅ Ready for Streamlit Cloud Deployment  
**Last Updated:** April 23, 2026  
**Deployed By:** GitHub Copilot
