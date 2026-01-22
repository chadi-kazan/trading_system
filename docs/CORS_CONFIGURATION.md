# CORS Configuration Guide

This document explains how Cross-Origin Resource Sharing (CORS) is configured in the Trading System API.

## Overview

The FastAPI backend supports flexible CORS configuration through both hardcoded defaults and environment variables, allowing you to control which frontend origins can access your API.

## Configuration Methods

### Method 1: Default Configuration (Recommended for Most Cases)

The API comes pre-configured with sensible defaults:

**Built-in Origins:**
- `http://localhost:5173` (Vite dev server)
- `http://127.0.0.1:5173` (Vite dev server)
- `http://localhost:3000` (Alternative dev server)
- `http://127.0.0.1:3000` (Alternative dev server)

**Built-in Regex Pattern:**
- `https://trading-system.*\.vercel\.app` (All Vercel deployments)

This default configuration allows:
- ✅ Local development on standard ports
- ✅ All Vercel preview and production deployments matching the pattern
- ✅ No environment variables needed for basic usage

### Method 2: Environment Variable - Additional Origins

Add specific origins without modifying code.

**Environment Variable:** `CORS_ORIGINS`

**Format:** Comma-separated list of URLs

**Example:**
```bash
# Single origin
CORS_ORIGINS="https://example.com"

# Multiple origins
CORS_ORIGINS="https://example.com,https://app.example.com,https://staging.example.com"
```

**Use Cases:**
- Adding a custom domain
- Adding multiple production deployments
- Testing from a specific URL

**On Render.com:**
1. Go to your service dashboard
2. Navigate to "Environment" tab
3. Add environment variable:
   - Key: `CORS_ORIGINS`
   - Value: `https://example.com,https://app.example.com`

### Method 3: Environment Variable - Custom Regex Pattern

Override the default regex pattern for more complex matching.

**Environment Variable:** `CORS_ORIGIN_REGEX`

**Format:** Python regex pattern

**Examples:**

```bash
# Allow all subdomains of yourdomain.com
CORS_ORIGIN_REGEX="https://.*\.yourdomain\.com"

# Allow multiple top-level domains
CORS_ORIGIN_REGEX="https://(app|staging|prod)\.example\.com"

# Allow both Vercel and Netlify deployments
CORS_ORIGIN_REGEX="https://trading-system.*\.(vercel|netlify)\.app"
```

**Use Cases:**
- Replacing the default Vercel pattern
- Supporting deployments on multiple platforms
- Complex subdomain matching

**On Render.com:**
1. Go to your service dashboard
2. Navigate to "Environment" tab
3. Add environment variable:
   - Key: `CORS_ORIGIN_REGEX`
   - Value: `https://.*\.yourdomain\.com`

## Configuration Priority

When both methods are used, they are **combined** (not mutually exclusive):

1. **Default localhost origins** (always included)
2. **+ Additional origins from** `CORS_ORIGINS`
3. **+ Regex pattern from** `CORS_ORIGIN_REGEX` (or default Vercel pattern)

**Example:**

```bash
CORS_ORIGINS="https://custom.example.com"
CORS_ORIGIN_REGEX="https://.*\.yourdomain\.com"
```

This configuration allows:
- ✅ `http://localhost:5173` (default)
- ✅ `http://127.0.0.1:5173` (default)
- ✅ `https://custom.example.com` (from CORS_ORIGINS)
- ✅ `https://app.yourdomain.com` (matches regex)
- ✅ `https://staging.yourdomain.com` (matches regex)
- ❌ `https://example.com` (not in list, doesn't match regex)

## Common Scenarios

### Scenario 1: Default Setup (No Configuration Needed)

**Situation:** Using Vercel for frontend, developing locally

**Configuration:** None needed! The defaults handle this.

**Allowed Origins:**
- Local development: `http://localhost:5173`
- Vercel production: `https://trading-system-three.vercel.app`
- Vercel previews: `https://trading-system-*.vercel.app`

---

### Scenario 2: Add Custom Production Domain

**Situation:** You have a custom domain `https://trading.mycompany.com`

**Configuration:**
```bash
CORS_ORIGINS="https://trading.mycompany.com"
```

**Result:** Custom domain added while keeping all defaults.

---

### Scenario 3: Multiple Custom Domains

**Situation:** Production + staging on custom domains

**Configuration:**
```bash
CORS_ORIGINS="https://trading.mycompany.com,https://staging-trading.mycompany.com"
```

**Result:** Both domains allowed, plus all defaults.

---

### Scenario 4: Deploy to Netlify Instead of Vercel

**Situation:** Migrating from Vercel to Netlify

**Configuration:**
```bash
CORS_ORIGIN_REGEX="https://trading-system.*\.netlify\.app"
```

**Result:** Netlify deployments allowed instead of Vercel.

---

### Scenario 5: Support Both Vercel and Custom Domain

**Situation:** Vercel for previews, custom domain for production

**Configuration:**
```bash
CORS_ORIGINS="https://trading.mycompany.com"
# Keep default regex for Vercel (no need to set CORS_ORIGIN_REGEX)
```

**Result:** Custom domain + all Vercel deployments.

---

### Scenario 6: Wildcard Subdomains

**Situation:** You have many subdomains: `app.`, `staging.`, `dev.`, etc.

**Configuration:**
```bash
CORS_ORIGIN_REGEX="https://.*\.mycompany\.com"
```

**Result:** All HTTPS subdomains of `mycompany.com` allowed.

## Security Considerations

### ✅ Good Practices

1. **Use specific patterns** instead of wildcard `*`
   ```bash
   # Good
   CORS_ORIGIN_REGEX="https://.*\.mycompany\.com"

   # Bad (too permissive)
   CORS_ORIGIN_REGEX=".*"
   ```

2. **Require HTTPS in production**
   ```bash
   # Good (HTTPS only)
   CORS_ORIGINS="https://example.com"

   # Risky (HTTP in production)
   CORS_ORIGINS="http://example.com"
   ```

3. **Be specific with regex patterns**
   ```bash
   # Good (specific app name)
   CORS_ORIGIN_REGEX="https://trading-system.*\.vercel\.app"

   # Too broad (allows any Vercel app)
   CORS_ORIGIN_REGEX="https://.*\.vercel\.app"
   ```

### ⚠️ What to Avoid

- **Don't use `allow_origins=["*"]`** - This disables important security features
- **Don't allow HTTP in production** - Only use HTTP for localhost
- **Don't use overly broad regex** - Be as specific as possible
- **Don't commit `.env` files** - Use `.env.example` as template

## Testing CORS Configuration

### Test from Browser Console

```javascript
// Open browser console on your frontend app
fetch('https://your-api.onrender.com/api/search?q=AAPL')
  .then(res => res.json())
  .then(data => console.log('Success:', data))
  .catch(err => console.error('CORS Error:', err));
```

**Expected Results:**
- ✅ **Success:** CORS is configured correctly
- ❌ **CORS Error:** Your origin is not allowed

### Test with cURL

```bash
# Test with Origin header
curl -H "Origin: https://your-frontend.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://your-api.onrender.com/api/search

# Check for Access-Control-Allow-Origin in response headers
```

### Verify Environment Variables

```bash
# On Render.com, check logs for startup
# The app will log CORS configuration if you add logging

# Temporarily add to app.py to debug:
import logging
logger = logging.getLogger(__name__)
logger.info(f"CORS Origins: {default_origins}")
logger.info(f"CORS Regex: {cors_regex}")
```

## Troubleshooting

### Issue: "CORS policy: No 'Access-Control-Allow-Origin' header is present"

**Cause:** Your frontend origin is not in the allowed list.

**Solutions:**
1. Add your origin to `CORS_ORIGINS`
2. Update `CORS_ORIGIN_REGEX` to match your domain
3. Check for typos in URLs (trailing slashes, http vs https)

---

### Issue: CORS works locally but not in production

**Cause:** Environment variables not set on deployment platform.

**Solutions:**
1. Verify environment variables are set on Render.com
2. Redeploy after adding environment variables
3. Check Render logs for actual CORS configuration

---

### Issue: Vercel preview deployments blocked

**Cause:** Preview deployment URL doesn't match regex pattern.

**Solutions:**
1. Check the exact preview URL format
2. Update regex to match: `https://trading-system.*\.vercel\.app`
3. Verify the pattern with a regex tester

---

### Issue: Works in development, fails in production

**Cause:** Different origins between dev and prod.

**Solutions:**
1. Check frontend's `VITE_API_BASE_URL` is correct
2. Ensure production frontend URL is in CORS config
3. Verify HTTPS is used in production

## Implementation Details

### Code Location

[dashboard_api/app.py](../dashboard_api/app.py)

### How It Works

```python
# 1. Start with default localhost origins
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# 2. Add origins from environment variable
env_origins = os.getenv("CORS_ORIGINS", "")
if env_origins:
    additional_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    default_origins.extend(additional_origins)

# 3. Get regex pattern (default or custom)
default_regex = r"https://trading-system.*\.vercel\.app"
cors_regex = os.getenv("CORS_ORIGIN_REGEX", default_regex)

# 4. Apply middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins,       # Exact matches
    allow_origin_regex=cors_regex,       # Pattern matches
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Quick Reference

| Scenario | Environment Variables | Example Values |
|----------|----------------------|----------------|
| Default (Vercel + localhost) | None | (uses defaults) |
| Add custom domain | `CORS_ORIGINS` | `https://trading.example.com` |
| Multiple custom domains | `CORS_ORIGINS` | `https://prod.example.com,https://staging.example.com` |
| Change deployment platform | `CORS_ORIGIN_REGEX` | `https://trading-system.*\.netlify\.app` |
| Wildcard subdomains | `CORS_ORIGIN_REGEX` | `https://.*\.example\.com` |
| Both regex and specific | Both | See Scenario 5 above |

## Resources

- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN CORS Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Python Regex Tester](https://regex101.com/)

---

**Last Updated:** 2026-01-22
