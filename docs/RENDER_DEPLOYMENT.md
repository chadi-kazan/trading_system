# Render.com Deployment Guide

Quick reference for deploying the Trading System API to Render.com.

## Environment Variables for Render

Add these environment variables in your Render.com service settings:

### Required Variables

None! The API works with defaults out of the box.

### Optional Variables for Production

#### CORS Configuration

```bash
# Add specific allowed origins (comma-separated)
CORS_ORIGINS=https://trading.mycompany.com,https://app.mycompany.com

# Override the default Vercel regex pattern
CORS_ORIGIN_REGEX=https://.*\.mycompany\.com
```

**Note:** By default, the API allows:
- All `https://trading-system-*.vercel.app` domains
- Local development on `localhost:5173` and `localhost:3000`

See [CORS Configuration Guide](CORS_CONFIGURATION.md) for detailed examples.

#### API Keys

```bash
# Alpha Vantage (for fundamentals data)
TS_ALPHA_VANTAGE_KEY=your_alpha_vantage_key

# FRED (for macro indicators)
TS_FRED_API_KEY=your_fred_api_key
```

#### Email Alerts

```bash
TS_EMAIL_SMTP_HOST=smtp.gmail.com
TS_EMAIL_SMTP_PORT=587
TS_EMAIL_USERNAME=your_email@gmail.com
TS_EMAIL_PASSWORD=your_app_password
TS_EMAIL_RECIPIENT=alerts@example.com
```

#### Database (Optional - defaults to SQLite)

```bash
# For PostgreSQL in production (recommended for multi-instance deployments)
DATABASE_URL=postgresql://user:password@host:port/database
```

## Deployment Steps

1. **Connect Repository**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   - Name: `trading-system-api`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn dashboard_api.app:app --host 0.0.0.0 --port $PORT`

3. **Add Environment Variables** (Optional)
   - Go to "Environment" tab
   - Add variables as needed (see above)
   - Click "Save Changes"

4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy
   - Your API will be available at: `https://your-service-name.onrender.com`

## Verifying Deployment

### 1. Check API Health

```bash
curl https://your-service-name.onrender.com/
```

Expected response:
```json
{
  "message": "Small-Cap Growth dashboard API",
  "docs": "/api/docs"
}
```

### 2. Check API Documentation

Visit: `https://your-service-name.onrender.com/api/docs`

### 3. Test CORS

From your frontend (browser console):
```javascript
fetch('https://your-service-name.onrender.com/api/search?q=AAPL')
  .then(res => res.json())
  .then(data => console.log('Success:', data))
  .catch(err => console.error('Error:', err));
```

## Updating Environment Variables

1. Go to your service in Render Dashboard
2. Navigate to "Environment" tab
3. Add/modify variables
4. **Important:** Click "Save Changes" - this will trigger a redeploy
5. Wait for the deployment to complete

## Common Issues

### CORS Errors After Deployment

**Symptom:** Frontend can't access the API

**Solution:** Add your frontend URL to environment variables:
```bash
CORS_ORIGINS=https://your-frontend-url.vercel.app
```

See [CORS Configuration Guide](CORS_CONFIGURATION.md) for detailed troubleshooting.

### Deployment Fails During Build

**Symptom:** Build fails with dependency errors

**Solution:** Ensure `requirements.txt` is up to date:
```bash
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update requirements.txt"
git push
```

### API Returns 500 Errors

**Symptom:** API endpoints return internal server errors

**Solution:** Check Render logs:
1. Go to your service dashboard
2. Click "Logs" tab
3. Look for Python tracebacks
4. Common issues:
   - Missing environment variables
   - Database connection issues
   - Missing data directories

## Monitoring

### View Logs

```bash
# Real-time logs in Render Dashboard
Dashboard → Your Service → Logs tab
```

### Check Metrics

```bash
# Render Dashboard shows:
# - CPU usage
# - Memory usage
# - Request count
# - Response times
```

## Automatic Deployments

Render automatically deploys when you push to your main branch:

1. Make changes to code
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push
   ```
3. Render detects the push and redeploys automatically
4. Check deployment status in Dashboard

## Free Tier Limitations

Render's free tier has these limitations:
- ⚠️ Service spins down after 15 minutes of inactivity
- ⚠️ Cold start can take 30-60 seconds
- ⚠️ Limited to 750 hours/month
- ⚠️ No custom domains

**Recommendation:** Upgrade to paid tier ($7/month) for production use.

## Production Recommendations

1. **Upgrade to Paid Tier**
   - Prevents cold starts
   - Better performance
   - Custom domain support

2. **Use PostgreSQL Database**
   - Add Render PostgreSQL service
   - Set `DATABASE_URL` environment variable
   - More reliable than SQLite for production

3. **Set Up Health Checks**
   - Render will ping your `/` endpoint
   - Automatically restarts if unhealthy

4. **Enable Auto-Deploy**
   - Already enabled by default
   - Deploys on every push to main branch

5. **Monitor Logs**
   - Check logs regularly for errors
   - Set up alerts for critical errors

## Connecting Frontend to API

After deploying, update your frontend environment variable:

**In `.env` file:**
```bash
VITE_API_BASE_URL=https://your-service-name.onrender.com
```

**Or set in Vercel:**
1. Go to Vercel project settings
2. Navigate to "Environment Variables"
3. Add:
   - Key: `VITE_API_BASE_URL`
   - Value: `https://your-service-name.onrender.com`
4. Redeploy frontend

## Resources

- [Render Documentation](https://render.com/docs)
- [Render Python Guide](https://render.com/docs/deploy-fastapi)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [CORS Configuration Guide](CORS_CONFIGURATION.md)

---

**Last Updated:** 2026-01-22
