# SPDCL ID Generator v2.0 - Railway Ready

## 🎯 Overview

Production-ready automation system for generating sequential IDs, scraping mobile numbers, and logging to Google Sheets. **Ready for Railway.com deployment.**

## ✨ Features

- **3-Status System**: NOT_STARTED → PENDING → COMPLETED
- **Sequential Processing**: One prefix at a time, PENDING first
- **Dynamic Range**: Auto-calculates max IDs from digit count
- **Intelligent Resume**: Automatically resumes from last position
- **Railway Ready**: Configured for Railway.com deployment

## 🚀 Quick Start

### Local Development
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
python run_complete_system.py
```

### Railway Deployment
See **`RAILWAY_SETUP_STEPS.md`** for detailed instructions.

**Quick Steps:**
1. Push to GitHub
2. Create Railway project
3. Connect GitHub repo
4. Add environment variables
5. Deploy!

## 📋 Environment Variables

Required for Railway:
```
SUPABASE_URL=your_url
SUPABASE_ANON_KEY=your_key
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

See `.env.example` for full list.

## 📁 Project Structure

```
.
├── app/              # Application code
├── run_complete_system.py  # Main entry point
├── requirements.txt  # Dependencies
├── railway.json     # Railway configuration
├── Procfile         # Alternative start command
└── README.md        # This file
```

## 🔧 Configuration

- **Railway**: Uses `railway.json` or `Procfile`
- **Service Account**: Supports JSON env var (Railway) or file path (local)
- **Database**: Supabase for prefix management
- **Sheets**: Google Sheets for data logging

## 📖 Documentation

- **`RAILWAY_SETUP_STEPS.md`** - Step-by-step Railway deployment
- **`RAILWAY_READY.md`** - Deployment readiness checklist

## 🔐 Security

- Environment variables for secrets
- Service account JSON in Railway env vars (encrypted)
- `.env` and `service-account.json` excluded from git

## 📊 Status

✅ **Production Ready**  
✅ **Railway Configured**  
✅ **All Dependencies Fixed**  
✅ **Clean Codebase**

---

**Version**: 2.0.0  
**Status**: Ready for Railway Deployment 🚂
