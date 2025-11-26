# 🚂 Railway.com Deployment - Step by Step

## ✅ Pre-Deployment Checklist

### 1. Clean Up Files (Optional)
```bash
python cleanup_for_railway.py
```
This removes test files, but they're already in `.gitignore` so won't be deployed anyway.

### 2. Verify Essential Files
- ✅ `app/` directory exists
- ✅ `run_complete_system.py` exists
- ✅ `requirements.txt` exists
- ✅ `railway.json` or `Procfile` exists
- ✅ `.gitignore` is updated

## 🚀 Railway Deployment Steps

### Step 1: Create Railway Account
1. Go to https://railway.com
2. Sign up/Login (use GitHub for easy repo connection)
3. Verify email if needed

### Step 2: Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub
4. Select your repository
5. Railway will auto-detect Python

### Step 3: Configure Environment Variables

In Railway dashboard → Your Service → Variables tab, add:

#### Required Variables:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
GOOGLE_SHEET_ID=your_google_sheet_id
```

#### Service Account (Choose ONE):

**Option A: JSON as Environment Variable (Recommended)**
```
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"...","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}
```
- Copy entire JSON from `service-account.json`
- Paste as single line (keep all quotes escaped)
- Remove newlines in private_key

**Option B: File Upload (Alternative)**
- Use Railway's volume feature
- Mount to `/app/service-account.json`
- Set: `GOOGLE_SERVICE_ACCOUNT_FILE=/app/service-account.json`

#### Optional Variables:
```
SCRAPER_ENABLED=true
SCRAPER_TIMEOUT=30
LOG_LEVEL=INFO
APP_NAME=SPDCL Automation
APP_VERSION=2.0.0
```

### Step 4: Deploy

Railway will automatically:
1. Detect Python from `requirements.txt`
2. Install dependencies
3. Run command from `Procfile` or `railway.json`
4. Start your application

### Step 5: Monitor Deployment

1. **View Logs**: Click on your service → "View Logs"
2. **Check Status**: Green = Running, Red = Error
3. **Verify**: Look for "Starting automation..." in logs

## 🔍 Verification

### Check Logs for:
```
✅ "Starting SEQUENTIAL prefix processing"
✅ "Found PENDING prefix to process"
✅ "Google Sheets client initialized"
✅ "Successfully logged to range"
```

### Common Issues:

**Build Fails:**
- Check `requirements.txt` syntax
- Verify Python version (Railway uses 3.12 by default)

**Runtime Error:**
- Check environment variables are set
- Verify service account JSON format
- Check logs for specific error

**Service Account Error:**
- Verify JSON is valid (use JSON validator)
- Ensure all quotes are escaped
- Check private_key has `\n` for newlines

## 📊 Post-Deployment

### Monitor:
- Railway dashboard logs
- Supabase for prefix status updates
- Google Sheets for new data

### Restart Service:
- Railway → Service → Settings → Restart

### Update Code:
- Push to GitHub
- Railway auto-deploys on push

## 🔐 Security Notes

- ✅ Never commit `.env` or `service-account.json` to git
- ✅ Use Railway's environment variables for secrets
- ✅ Service account JSON in env var is encrypted by Railway
- ✅ Railway provides HTTPS automatically

## 💰 Railway Pricing

- **Free Tier**: $5 credit/month
- **Hobby Plan**: $5/month (if needed)
- Check Railway pricing page for current rates

## 🆘 Support

If deployment fails:
1. Check Railway logs
2. Verify all environment variables
3. Test locally first with same env vars
4. Check Railway status page

---

**Your app is now live on Railway! 🎉**

