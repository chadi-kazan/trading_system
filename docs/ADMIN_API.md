# Admin API Endpoints

Remote administration endpoints for refreshing Russell 2000, S&P 500, and fundamentals data on deployed instances.

## Overview

The Admin API provides HTTP endpoints to trigger data refresh operations that would normally require CLI access. This is particularly useful for cloud deployments (like Render.com) where you don't have direct shell access.

**Base Path:** `/api/admin`

## Authentication

✅ **All admin endpoints require API key authentication.**

### Setup

1. Generate a secure API key:
   ```bash
   python -c "from dashboard_api.auth import generate_api_key; print(generate_api_key())"
   ```

2. Set the environment variable:
   ```bash
   export ADMIN_API_KEY="your-generated-key-here"
   ```

3. Include the key in all requests:
   ```bash
   curl -X POST https://your-api.onrender.com/api/admin/refresh-russell \
     -H "X-Admin-API-Key: your-generated-key-here"
   ```

### Response Codes

| Code | Meaning |
|------|---------|
| 401 | Missing `X-Admin-API-Key` header |
| 403 | Invalid API key |
| 503 | `ADMIN_API_KEY` environment variable not configured on server |

### Security Best Practices

1. Use a strong, randomly generated key (32+ characters)
2. Rotate keys periodically
3. Never commit keys to version control
4. Use different keys for staging and production

## Endpoints

### 1. Check Refresh Status

Get information about when data was last refreshed.

**Request:**
```http
GET /api/admin/refresh-status
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "russell_2000": {
      "exists": true,
      "last_modified": "2026-01-22T15:30:00"
    },
    "fundamentals_cache": {
      "exists": true,
      "file_count": 2543
    }
  }
}
```

**cURL Example:**
```bash
curl https://your-api.onrender.com/api/admin/refresh-status \
  -H "X-Admin-API-Key: your-api-key"
```

---

### 2. Refresh Russell 2000

Download the latest Russell 2000 constituent list.

**Request:**
```http
POST /api/admin/refresh-russell
```

**Response:**
```json
{
  "status": "success",
  "message": "Russell 2000 constituent list refreshed successfully",
  "output": "Downloaded 2000 symbols\nSaved to data/universe/russell_2000.csv"
}
```

**cURL Example:**
```bash
curl -X POST https://your-api.onrender.com/api/admin/refresh-russell \
  -H "X-Admin-API-Key: your-api-key"
```

**Execution Time:** ~10-30 seconds

**Notes:**
- Updates `data/universe/russell_2000.csv`
- Safe to run frequently (data doesn't change often)
- No API keys required

---

### 3. Refresh Fundamentals

Fetch fundamentals data from Alpha Vantage for universe symbols.

**Request:**
```http
POST /api/admin/refresh-fundamentals?include_russell=true&include_sp500=true&limit=200
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_russell` | boolean | `true` | Include Russell 2000 constituents |
| `include_sp500` | boolean | `true` | Include S&P 500 constituents |
| `limit` | integer | `200` | Maximum number of symbols to refresh |

**Response:**
```json
{
  "status": "success",
  "message": "Fundamentals cache refreshed successfully",
  "parameters": {
    "include_russell": true,
    "include_sp500": true,
    "limit": 200
  },
  "output": "Refreshed 200 symbols\n45 cached\n155 fetched from API\n..."
}
```

**cURL Examples:**

```bash
# Default: Include both Russell and S&P 500, limit 200
curl -X POST https://your-api.onrender.com/api/admin/refresh-fundamentals \
  -H "X-Admin-API-Key: your-api-key"

# Russell only, limit 100
curl -X POST "https://your-api.onrender.com/api/admin/refresh-fundamentals?include_russell=true&include_sp500=false&limit=100" \
  -H "X-Admin-API-Key: your-api-key"

# S&P 500 only, limit 50
curl -X POST "https://your-api.onrender.com/api/admin/refresh-fundamentals?include_russell=false&include_sp500=true&limit=50" \
  -H "X-Admin-API-Key: your-api-key"
```

**Execution Time:**
- With free tier Alpha Vantage (5 calls/min): ~40-50 minutes for 200 symbols
- With premium tier: ~2-5 minutes

**Notes:**
- Requires `TS_ALPHA_VANTAGE_KEY` environment variable
- Updates `data/universe/fundamentals/*.json`
- Free tier is rate-limited to 5 API calls/minute
- The endpoint will wait and respect rate limits automatically
- May timeout on free tier Render.com (15 min limit) for large refreshes

**Rate Limit Handling:**
- Uses built-in throttling (12 seconds between calls by default)
- Respects Alpha Vantage 429 errors
- Caches previously fetched data to avoid re-fetching

---

### 4. Refresh All Data

Convenience endpoint that runs both Russell and fundamentals refresh sequentially.

**Request:**
```http
POST /api/admin/refresh-all
```

**Response:**
```json
{
  "status": "success",
  "message": "All data refreshed successfully",
  "russell": {
    "status": "success",
    "message": "Russell 2000 constituent list refreshed successfully",
    "output": "..."
  },
  "fundamentals": {
    "status": "success",
    "message": "Fundamentals cache refreshed successfully",
    "parameters": {
      "include_russell": true,
      "include_sp500": true,
      "limit": 200
    },
    "output": "..."
  }
}
```

**cURL Example:**
```bash
curl -X POST https://your-api.onrender.com/api/admin/refresh-all \
  -H "X-Admin-API-Key: your-api-key"
```

**Execution Time:** ~40-60 minutes (dominated by fundamentals refresh)

**Notes:**
- Runs Russell refresh first, then fundamentals
- Uses default parameters for fundamentals (both universes, limit 200)
- May timeout on free tier Render.com
- Consider running separately or reducing the limit

---

## Error Responses

### 500 Internal Server Error

**Causes:**
- CLI command failed
- File system permissions issues
- Missing dependencies

**Example:**
```json
{
  "detail": "Russell refresh failed: Command 'python main.py refresh-russell' returned non-zero exit status 1"
}
```

### 504 Gateway Timeout

**Causes:**
- Operation exceeded timeout limit
- Too many symbols to refresh
- API rate limiting delays

**Example:**
```json
{
  "detail": "Fundamentals refresh timed out (>10min). Try reducing the limit parameter."
}
```

**Solution:** Reduce the `limit` parameter or run in smaller batches.

---

## Usage Patterns

### Daily Refresh Schedule

Use a cron job or external scheduler to hit the refresh endpoints:

**Using cURL (Linux/macOS cron):**
```bash
# Every day at 2 AM, refresh Russell
0 2 * * * curl -X POST https://your-api.onrender.com/api/admin/refresh-russell -H "X-Admin-API-Key: $ADMIN_API_KEY"

# Every Sunday at 3 AM, refresh fundamentals (50 at a time)
0 3 * * 0 curl -X POST "https://your-api.onrender.com/api/admin/refresh-fundamentals?limit=50" -H "X-Admin-API-Key: $ADMIN_API_KEY"
```

**Using GitHub Actions:**

Create `.github/workflows/refresh-data.yml`:
```yaml
name: Refresh Trading Data

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:  # Allow manual trigger

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - name: Refresh Russell 2000
        run: |
          curl -X POST https://your-api.onrender.com/api/admin/refresh-russell \
            -H "X-Admin-API-Key: ${{ secrets.ADMIN_API_KEY }}"

      - name: Refresh Fundamentals (Small Batch)
        run: |
          curl -X POST "https://your-api.onrender.com/api/admin/refresh-fundamentals?limit=50" \
            -H "X-Admin-API-Key: ${{ secrets.ADMIN_API_KEY }}"
```

**Note:** Add `ADMIN_API_KEY` to your GitHub repository secrets.

---

### Manual Refresh via Browser

Navigate to the API documentation:
```
https://your-api.onrender.com/api/docs
```

1. Expand the `/api/admin/refresh-status` endpoint
2. Click "Try it out"
3. Click "Execute"
4. View the response to see current data status

Then trigger refreshes as needed using the other endpoints.

---

### Batch Refresh Strategy (Free Tier)

To avoid timeouts on free tier, refresh in small batches:

```bash
# Day 1: Refresh Russell
curl -X POST https://your-api.onrender.com/api/admin/refresh-russell

# Day 2: Refresh 50 fundamentals
curl -X POST "https://your-api.onrender.com/api/admin/refresh-fundamentals?limit=50&include_russell=true&include_sp500=false"

# Day 3: Refresh another 50
curl -X POST "https://your-api.onrender.com/api/admin/refresh-fundamentals?limit=50&include_russell=false&include_sp500=true"

# Repeat over several days to build up the cache
```

---

---

## Monitoring

### Check Logs

After triggering a refresh, check Render logs:

1. Go to Render Dashboard
2. Select your service
3. Click "Logs" tab
4. Look for output from the CLI commands

### Verify Results

Check the status endpoint to confirm data was updated:

```bash
curl https://your-api.onrender.com/api/admin/refresh-status
```

Look for updated `last_modified` timestamp and increased `file_count`.

---

## Troubleshooting

### Issue: "Command not found" or "Permission denied"

**Cause:** CLI not in PATH or file permissions

**Fix:** Ensure `main.py` is executable and in the project root

---

### Issue: Timeout on fundamentals refresh

**Cause:** Too many symbols, API rate limits

**Solutions:**
1. Reduce `limit` parameter to 50 or less
2. Run multiple smaller batches over several days
3. Upgrade to Alpha Vantage premium tier
4. Upgrade Render.com to paid tier (no timeout)

---

### Issue: "Alpha Vantage API key not set"

**Cause:** Missing environment variable

**Fix:** Set `TS_ALPHA_VANTAGE_KEY` on Render.com:
1. Dashboard → Environment tab
2. Add variable: `TS_ALPHA_VANTAGE_KEY=your_key`
3. Save (triggers redeploy)

---

### Issue: Refresh completes but data not reflected

**Cause:** Data cached in memory or not persisted

**Solutions:**
1. Check file system on Render (may be ephemeral)
2. Verify `data/` directory is writable
3. Consider using persistent storage or S3 for cache

---

## Alternative: Local Refresh + Git Push

If admin endpoints are problematic, refresh locally and commit:

```bash
# Run locally
python main.py refresh-russell
python main.py refresh-fundamentals --include-russell --include-sp500 --limit 200

# Commit and push
git add data/universe/
git commit -m "Update Russell 2000 and fundamentals cache"
git push

# Render auto-deploys with updated data
```

This is often simpler and avoids timeout issues on free tier.

---

## API Documentation

Access interactive API docs at:
```
https://your-api.onrender.com/api/docs
```

All admin endpoints are listed under the "Admin" tag.

---

**Last Updated:** 2026-01-22
