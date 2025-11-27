# 🔄 Keep-Alive Setup for Render Free Tier

## Why This is Needed

Render's **free tier** automatically shuts down services after **15 minutes of inactivity**. Even though your automation runs in the background, Render only counts **external HTTP requests** as activity.

Without external traffic, your service will be shut down, interrupting your automation.

## ✅ Solution: External Ping Service (FREE)

The best solution is to use a **free external service** to ping your Render service every 10-12 minutes. This keeps your service active 24/7 on the free tier.

## 🚀 Quick Setup (5 minutes)

### Option 1: UptimeRobot (Recommended - Easiest)

1. **Sign up** (free): https://uptimerobot.com
2. **Add Monitor**:
   - Monitor Type: **HTTP(s)**
   - Friendly Name: `SPDCL Automation Keep-Alive`
   - URL: `https://your-service-name.onrender.com/`
   - Monitoring Interval: **10 minutes**
3. **Click "Create Monitor"**
4. **Done!** Your service will be pinged every 10 minutes

**Free tier includes**: 50 monitors, 5-minute minimum interval

---

### Option 2: cron-job.org (Alternative)

1. **Sign up** (free): https://cron-job.org
2. **Create Cronjob**:
   - Title: `SPDCL Keep-Alive`
   - URL: `https://your-service-name.onrender.com/`
   - Schedule: Every **10 minutes** (`*/10 * * * *`)
3. **Click "Create Cronjob"**
4. **Done!**

---

### Option 3: EasyCron (Alternative)

1. **Sign up** (free): https://www.easycron.com
2. **Create Cron Job**:
   - URL: `https://your-service-name.onrender.com/`
   - Cron Expression: `*/10 * * * *` (every 10 minutes)
3. **Save**

---

## 📋 What URL to Use?

Use your Render service URL. You can find it in:
- Render Dashboard → Your Service → Settings → **Service URL**
- Format: `https://your-service-name.onrender.com/`

The health endpoint is at the root (`/`), so just use your service URL.

---

## 🔍 Verify It's Working

After setting up the external ping service:

1. **Check Render logs** - You should see requests every 10 minutes:
   ```
   INFO:     127.0.0.1:xxxxx - "GET / HTTP/1.1" 200 OK
   ```

2. **Check UptimeRobot/cron-job dashboard** - Should show successful pings

3. **Monitor your automation** - It should continue running without interruption

---

## ⚙️ Internal Keep-Alive (Already Configured)

Your application already has an **internal keep-alive service** that:
- Pings the health endpoint every 5 minutes
- Uses external URL if available (from `RENDER_EXTERNAL_URL` env var)
- Falls back to localhost if external URL not available

**However**, internal pings may not count as "external traffic" for Render's purposes. That's why the **external ping service is recommended**.

---

## 🎯 Best Practice

**Use BOTH**:
1. ✅ Internal keep-alive (already configured) - as backup
2. ✅ External ping service (set up above) - primary solution

This ensures maximum reliability.

---

## 💡 Pro Tips

1. **Set interval to 10 minutes** - Well under Render's 15-minute timeout, with buffer
2. **Monitor the monitor** - Check UptimeRobot dashboard occasionally to ensure it's working
3. **Use HTTPS** - Render services use HTTPS, so use `https://` in your ping URL
4. **Test first** - After setting up, wait 15+ minutes and check if your service is still running

---

## 🆘 Troubleshooting

### Service still shutting down?

1. **Check ping service is active**: Verify in UptimeRobot/cron-job dashboard
2. **Verify URL is correct**: Test the URL in browser - should return `{"status": "live", ...}`
3. **Check Render logs**: Look for incoming requests from ping service
4. **Reduce interval**: Try 8-9 minutes instead of 10 (but stay above 5 minutes to avoid rate limits)

### Can't find service URL?

1. Go to Render Dashboard
2. Click on your service
3. Look for "Service URL" or "URL" in the service details
4. It should be something like: `https://spdcl-automation-xxxxx.onrender.com`

---

## 📊 Expected Behavior

With external ping service configured:
- ✅ Service stays active 24/7
- ✅ Automation runs continuously
- ✅ No unexpected shutdowns
- ✅ Free tier compatible

---

## 🔗 Quick Links

- **UptimeRobot**: https://uptimerobot.com
- **cron-job.org**: https://cron-job.org
- **EasyCron**: https://www.easycron.com
- **Render Docs**: https://render.com/docs/free-tier

---

**Need help?** Check your Render logs for keep-alive ping messages:
```
💓 Keep-alive ping #X successful - service remains active
```

