# Render Deployment Diagnostic Checklist

## 🔍 Current Issue
**Port scan timeout** - Render cannot detect an open port, meaning the web server is NOT starting.

## 📋 What to Check in Render Dashboard

### 1. Service Type
- Go to: **Your Service → Settings**
- Check: **Service Type** should be **"Web Service"** (NOT "Background Worker")

### 2. Start Command
- Go to: **Your Service → Settings → Start Command**
- **What command is shown?**
  - ✅ CORRECT: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info`
  - ❌ WRONG: `python run_complete_system.py` or anything else

### 3. Build Logs
- Go to: **Your Service → Logs**
- Scroll to the **very beginning** of the deploy
- Look for: `==> Running '...'` or `Executing: ...`
- **What command appears there?**

### 4. Deploy Logs
- In the logs, look for:
  - `🚀 Starting FastAPI web server...` (should appear)
  - `Uvicorn running on http://0.0.0.0:XXXX` (should appear)
  - `Application startup complete` (should appear)
  
- If you see:
  - `Generating ID: 2626...` ❌ (this means automation script is running, not web server)
  - `Starting automation...` ❌ (wrong command)

## 🔧 Quick Fixes to Try

### Fix 1: Manual Override in Dashboard
1. Go to **Settings → Start Command**
2. **Manually set** (even if it shows the correct command):
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info
   ```
3. **Save** and **Redeploy**

### Fix 2: Verify render.yaml is Being Used
- Render should auto-detect `render.yaml` in the root
- If you have a `Procfile`, it might take precedence
- I've renamed `Procfile` to `Procfile.backup` to force Render to use `render.yaml`

### Fix 3: Check Environment Variables
- Go to: **Settings → Environment**
- Verify `PORT` is NOT manually set (Render sets this automatically)
- Verify other required vars are set:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `GOOGLE_SHEET_ID`
  - `GOOGLE_SERVICE_ACCOUNT_JSON`

## 📊 What the Logs Should Show (Correct)

```
==> Running 'uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info'
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
🚀 Starting FastAPI web server...
🌐 Web server will bind to 0.0.0.0:$PORT
```

## ❌ What You're Currently Seeing (Wrong)

```
Generating ID: 2626 09417
Scraping mobile number for: 2626 09417
Progress: 9424/99999
```

This means the **automation script** is running, NOT the web server.

## 🎯 Next Steps

1. **Check the Render Dashboard** using the checklist above
2. **Share with me:**
   - What Start Command is shown in Settings?
   - What command appears in the build logs?
   - Is the service type "Web Service" or "Background Worker"?
3. **Then I can provide the exact fix**

