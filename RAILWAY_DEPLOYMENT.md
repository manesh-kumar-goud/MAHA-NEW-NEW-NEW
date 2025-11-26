# 🚂 Railway.com Deployment Guide

## Pre-Deployment Cleanup

### Files to Remove (Already in .gitignore)
- All `test_*.py` files
- All `*.ps1` files
- Diagnostic scripts (`diagnose_*.py`, `fix_*.py`)
- Extra documentation files (keep only README.md)
- Log files (`*.log`)

### Files to Keep
- `app/` directory (all application code)
- `run_complete_system.py` (main entry point)
- `requirements.txt` (dependencies)
- `README.md` (documentation)
- `sql/` directory (for reference)
- `Dockerfile` (optional, Railway can auto-detect)
- `.gitignore`
- `railway.json` (Railway config - we'll create this)
- `Procfile` (Railway start command - we'll create this)

## Railway Setup Steps

### 1. Prepare Repository

```bash
# Ensure .gitignore is updated
# Remove unwanted files (they're already ignored)
git add .
git commit -m "Prepare for Railway deployment"
```

### 2. Create Railway Account
- Go to https://railway.com
- Sign up/Login with GitHub
- Create new project

### 3. Connect Repository
- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose your repository
- Railway will auto-detect Python

### 4. Configure Environment Variables

In Railway dashboard, add these variables:

```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=/app/service-account.json
SCRAPER_ENABLED=true
SCRAPER_TIMEOUT=30
LOG_LEVEL=INFO
APP_NAME=SPDCL Automation
APP_VERSION=2.0.0
```

### 5. Add Service Account File

**Option A: Environment Variable (Recommended)**
- In Railway, go to Variables
- Add variable: `GOOGLE_SERVICE_ACCOUNT_JSON`
- Paste entire JSON content from `service-account.json`
- Update code to read from env var (we'll create this)

**Option B: Railway Volume**
- Add volume in Railway
- Mount to `/app/service-account.json`
- Upload file manually

### 6. Deploy

Railway will automatically:
- Detect Python
- Install dependencies from `requirements.txt`
- Run command from `Procfile` or `railway.json`

## Railway Configuration Files

### railway.json (Created below)
Defines build and start commands

### Procfile (Created below)
Simple start command (alternative to railway.json)

## Post-Deployment

1. Check logs in Railway dashboard
2. Verify Supabase connection
3. Verify Google Sheets access
4. Monitor automation status

## Troubleshooting

- **Build fails**: Check `requirements.txt` syntax
- **Runtime error**: Check environment variables
- **Service account error**: Verify JSON format in env var
- **Database error**: Verify Supabase credentials

