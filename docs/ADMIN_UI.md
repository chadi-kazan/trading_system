# Admin UI Guide

## Overview

The Admin UI provides a web interface for managing data refresh operations in the Trading System. It requires authentication via API key to access protected admin endpoints.

## Access

Navigate to: `http://localhost:3000/admin` (or your deployed URL + `/admin`)

## Features

### 1. **Authentication**
- Login screen requires admin API key
- API key is stored in localStorage for persistence
- Logout clears stored credentials

### 2. **Data Status Dashboard**
- Shows last updated timestamps for:
  - Russell 2000 constituents
  - Fundamentals cache

### 3. **Refresh Operations**

Three refresh actions available:

1. **Refresh Russell 2000 Constituents**
   - Downloads latest Russell 2000 list
   - Updates: `data/universe/russell_2000.csv`
   - Recommended frequency: Weekly

2. **Refresh Fundamentals**
   - Fetches earnings, P/E, market cap from Alpha Vantage
   - Updates: `data/universe/fundamentals/{SYMBOL}.json`
   - Rate limited: 5 calls/min (free tier)
   - Recommended frequency: Weekly or monthly

3. **Refresh All**
   - Runs both Russell and Fundamentals refresh sequentially
   - Use for comprehensive data updates

### 4. **Operation Feedback**
- Real-time status for each operation (Running/Success/Error)
- Success messages show completion status
- Error messages display failure reasons
- Status dashboard auto-refreshes after operations

## Setup

### 1. Generate Admin API Key

```bash
python -c "from dashboard_api.auth import generate_api_key; print(generate_api_key())"
```

### 2. Set Environment Variable

**Option A: .env file (recommended)**
```bash
# In .env file
ADMIN_API_KEY=your-generated-key-here
```

**Option B: Export in shell**
```bash
# Linux/macOS
export ADMIN_API_KEY=your-generated-key-here

# Windows
set ADMIN_API_KEY=your-generated-key-here
```

### 3. Start the API Server

```bash
uvicorn dashboard_api.app:app --reload
```

### 4. Start the Frontend

```bash
cd dashboard_web
npm run dev
```

### 5. Navigate to Admin Page

Open browser: `http://localhost:3000/admin`

## Security Notes

- API key is stored in browser localStorage (client-side only)
- All admin endpoints require `X-Admin-API-Key` header
- API key verification uses constant-time comparison
- Invalid keys return 403 Forbidden
- Missing API key configuration returns 503 Service Unavailable

## Usage Tips

1. **Weekly Maintenance**
   - Refresh Russell constituents once per week (minimal changes)
   - Refresh fundamentals weekly or bi-weekly depending on needs

2. **Rate Limiting**
   - Alpha Vantage free tier: 5 calls/min, 500/day
   - Large fundamentals refresh may take hours
   - Consider upgrading to premium tier for production

3. **Automation Alternative**
   - For scheduled automation, use CLI instead:
     ```bash
     python main.py refresh-russell
     python main.py refresh-fundamentals --include-russell --include-sp500
     ```
   - Set up cron job or Windows Task Scheduler for automated runs

4. **Monitoring**
   - Check "Data Status" section for last update timestamps
   - Stale data (>7 days old) should be refreshed
   - Monitor operation feedback for failures

## Troubleshooting

### Issue: "Invalid API key" on login
**Solution:**
- Verify ADMIN_API_KEY is set in environment
- Restart API server after setting env variable
- Regenerate key if needed

### Issue: "Admin endpoints are not configured"
**Solution:**
- ADMIN_API_KEY environment variable not set
- Add to `.env` file or export in shell
- Restart API server

### Issue: Operation takes too long / times out
**Solution:**
- Fundamentals refresh can take hours with free tier rate limits
- Use CLI with `--limit` flag to refresh subset
- Consider upgrading Alpha Vantage tier

### Issue: "Unexpected error" during refresh
**Solution:**
- Check API server logs for details
- Verify internet connection (downloads from external sources)
- Ensure sufficient disk space for cache files

## API Endpoints

The Admin UI calls these backend endpoints:

- `POST /api/admin/refresh-russell` - Refresh Russell 2000
- `POST /api/admin/refresh-fundamentals` - Refresh fundamentals
- `POST /api/admin/refresh-all` - Refresh everything
- `GET /api/admin/refresh-status` - Get data timestamps

See [docs/ADMIN_API.md](ADMIN_API.md) for complete API documentation.

## Related Documentation

- [ADMIN_API.md](ADMIN_API.md) - Backend API reference
- [CLI_USAGE.md](../CLI_USAGE.md) - CLI commands for automation
- [CLAUDE.md](../CLAUDE.md) - Developer guide

---

**Last Updated:** 2026-01-29
