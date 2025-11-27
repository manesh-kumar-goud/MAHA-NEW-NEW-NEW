# How to Check if Automation is Running

## 🔍 Method 1: Check Render Logs

1. Go to **Render Dashboard** → Your Service → **Logs**
2. Look for these messages (should appear ~15 seconds after server start):

### ✅ Automation Started Successfully:
```
Server mode detected - initializing background automation...
✅ Background automation thread scheduled (will wait 15s before starting)
Waiting 15 seconds for web server to fully bind to port...
Starting background automation...
Checking Supabase for existing automation tasks...
Starting automation for X prefixes
🎯 Processing prefix: XXXX
Generating ID: XXXX XXXXX
Scraping mobile number for: XXXX XXXXX
```

### ❌ No Prefixes to Process:
```
No prefixes to automate - will check periodically
```

## 🔍 Method 2: Check via API Endpoint

Visit this URL in your browser:
```
https://maha-new-new-new-1.onrender.com/api/v1/automation/status
```

**Expected Response if Running:**
```json
{
  "running": true,
  "total_generated": 150,
  "mobile_numbers_found": 5,
  "errors": 2,
  "runtime_seconds": 3600.5,
  "success_rate": 98.67
}
```

**Expected Response if NOT Running:**
```json
{
  "running": false,
  "total_generated": 0,
  "mobile_numbers_found": 0,
  "errors": 0,
  "runtime_seconds": null,
  "success_rate": 0.0
}
```

## 🔍 Method 3: Check Health Endpoint

Visit:
```
https://maha-new-new-new-1.onrender.com/health
```

Look for:
```json
{
  "status": "running",
  "automation": {
    "running": true,  // ← This should be true if automation is active
    "generated": 150,
    "found": 5
  }
}
```

## 🔍 Method 4: Check Database

If you have access to Supabase:
- Check `prefix_metadata` table
- Look for prefixes with status `PENDING` or `NOT_STARTED`
- If all are `COMPLETED`, automation will wait for new work

## ⚠️ Common Issues

### Issue 1: No Prefixes in Database
- **Symptom**: Logs show "No prefixes to automate"
- **Solution**: Add prefixes to database with status `PENDING` or `NOT_STARTED`

### Issue 2: All Prefixes Completed
- **Symptom**: Automation checks but finds no work
- **Solution**: Reset a prefix status to `PENDING` or add new prefixes

### Issue 3: Automation Not Starting
- **Symptom**: No automation logs after 15 seconds
- **Check**: Look for error messages in logs
- **Solution**: Check environment variables (SUPABASE_URL, SUPABASE_ANON_KEY)

## 📊 What Automation Does When Running

1. **Generates IDs** every 5 seconds (configurable)
2. **Scrapes mobile numbers** from https://tgsouthernpower.org
3. **Logs to Google Sheets** (if configured)
4. **Updates database** with results
5. **Continues until** all prefixes are COMPLETED

## 🎯 Quick Test

Run this command to see current status:
```bash
curl https://maha-new-new-new-1.onrender.com/api/v1/automation/status
```

Or visit in browser:
https://maha-new-new-new-1.onrender.com/api/v1/automation/status

