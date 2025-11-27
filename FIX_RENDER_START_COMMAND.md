# 🔧 Fix Render Start Command

## ❌ Current (WRONG)
```
Start Command: python run_complete_system.py
```

## ✅ Correct Start Command
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info
```

## 📝 Steps to Fix

1. **Go to Render Dashboard**
   - Navigate to your service: `spdcl-automation`

2. **Open Settings**
   - Click on **Settings** tab

3. **Find "Start Command"**
   - Scroll down to the **Start Command** field

4. **Replace the command**
   - **DELETE:** `python run_complete_system.py`
   - **ENTER:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info`

5. **Save**
   - Click **Save Changes**

6. **Redeploy**
   - Go to **Manual Deploy** → **Deploy latest commit**
   - OR wait for auto-deploy if you push new changes

## ✅ After Fix, You Should See in Logs:

```
==> Running 'uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info'
INFO:     Started server process
INFO:     Waiting for application startup.
🚀 Starting FastAPI web server...
🌐 Web server will bind to 0.0.0.0:$PORT
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
```

## 🎯 Why This Fixes It

- `python run_complete_system.py` = Runs automation script (no web server) ❌
- `uvicorn app.main:app ...` = Starts FastAPI web server (exposes HTTP port) ✅

Render needs a web server listening on a port to mark the service as "live".

