# App-Wide Authentication Guide

## Overview

The Trading System uses a simple, shared API key authentication system to protect all application endpoints. This ensures only authorized users can access the dashboard and API.

## Architecture

**Authentication Type:** Single Shared API Key (Option 3)

- **Backend:** FastAPI dependency injection enforces `X-App-Access-Key` header on all `/api/*` endpoints
- **Frontend:** React context + localStorage stores access key and injects it into all API requests
- **Security:** Constant-time key comparison prevents timing attacks
- **Stateless:** No sessions or database required

## Setup Instructions

### 1. Generate App Access Key

```bash
python -c "from dashboard_api.auth import generate_api_key; print(generate_api_key())"
```

Example output:
```
xJk3n8Pq9rLmT4vW2zY5sB7cD1fG6hN0
```

### 2. Configure Backend

**Option A: Using .env file (Recommended)**

Add to `.env`:
```bash
APP_ACCESS_KEY=xJk3n8Pq9rLmT4vW2zY5sB7cD1fG6hN0
```

**Option B: Environment Variable**

```bash
# Linux/macOS
export APP_ACCESS_KEY=xJk3n8Pq9rLmT4vW2zY5sB7cD1fG6hN0

# Windows
set APP_ACCESS_KEY=xJk3n8Pq9rLmT4vW2zY5sB7cD1fG6hN0
```

### 3. Restart API Server

```bash
uvicorn dashboard_api.app:app --reload
```

### 4. Start Frontend

```bash
cd dashboard_web
npm run dev
```

### 5. Access Application

1. Navigate to `http://localhost:3000`
2. You'll see the login screen
3. Enter the `APP_ACCESS_KEY` you generated
4. Click "Sign In"
5. Access key is stored in browser localStorage for future visits

## User Experience

### Login Flow

1. **First Visit:**
   - User sees login screen
   - Enters access key
   - Frontend verifies key by making test API call
   - On success, key is stored in localStorage
   - User is redirected to main app

2. **Subsequent Visits:**
   - Access key auto-loaded from localStorage
   - User goes directly to main app
   - No login required

3. **Logout:**
   - Available in Admin panel or can be added to main nav
   - Clears localStorage
   - Returns to login screen

### Error Handling

- **Invalid Key:** "Invalid access key" error shown on login
- **Missing Key:** Login screen displayed
- **Expired/Revoked Key:** Automatic logout on 401/403 response

## Security Features

### Backend Protection

All API endpoints require `X-App-Access-Key` header:

```python
# In dashboard_api/routes/__init__.py
api_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(require_app_access_key)]
)
```

### Frontend Integration

All API calls automatically include the access key:

```typescript
// In dashboard_web/src/api.ts
function getAuthHeaders(): Record<string, string> {
  const accessKey = localStorage.getItem("app_access_key");
  return accessKey ? { "X-App-Access-Key": accessKey } : {};
}
```

### Constant-Time Comparison

Prevents timing attacks:

```python
# In dashboard_api/auth.py
def verify_api_key(api_key: str, expected_key: str) -> bool:
    return hmac.compare_digest(api_key, expected_key)
```

## Admin Endpoints

Admin endpoints require **both** keys:

1. **APP_ACCESS_KEY** - Required for all /api/* endpoints
2. **ADMIN_API_KEY** - Additional protection for /api/admin/* endpoints

Example admin request:
```bash
curl -X POST http://localhost:8000/api/admin/refresh-russell \
  -H "X-App-Access-Key: your-app-key" \
  -H "X-Admin-API-Key: your-admin-key"
```

From the Admin UI, both keys are automatically included.

## Key Management

### Rotating the Access Key

1. **Generate new key:**
   ```bash
   python -c "from dashboard_api.auth import generate_api_key; print(generate_api_key())"
   ```

2. **Update backend:**
   - Edit `.env` file
   - Update `APP_ACCESS_KEY=new-key`
   - Restart API server

3. **Distribute to users:**
   - All users must update their stored key
   - They'll be automatically logged out
   - Login with new key

### Key Storage Security

- **Backend:** Environment variable (never hardcode)
- **Frontend:** Browser localStorage (client-side only)
- **Transit:** HTTPS required in production
- **Never commit:** `.env` is gitignored

## Deployment Considerations

### Production Checklist

- [ ] Generate strong access key (32+ characters)
- [ ] Set `APP_ACCESS_KEY` in production environment
- [ ] Enable HTTPS/TLS for all traffic
- [ ] Configure CORS for your domain
- [ ] Set `VITE_API_BASE_URL` to production API URL
- [ ] Consider key rotation policy

### Environment Variables

```bash
# Production .env
APP_ACCESS_KEY=production-key-here
ADMIN_API_KEY=admin-key-here
CORS_ORIGINS=https://yourdomain.com
```

### Render.com Deployment

In Render dashboard:
1. Go to your web service
2. Navigate to "Environment" tab
3. Add:
   - `APP_ACCESS_KEY` = your generated key
   - `ADMIN_API_KEY` = admin key
4. Save and redeploy

### Vercel Deployment (Frontend)

In Vercel dashboard:
1. Go to project settings
2. Navigate to "Environment Variables"
3. Add:
   - `VITE_API_BASE_URL` = your API URL (e.g., `https://api.yourdomain.com`)
4. Redeploy

## Troubleshooting

### Issue: "Missing access key" on login
**Cause:** Backend `APP_ACCESS_KEY` not set

**Solution:**
1. Check `.env` file exists
2. Verify `APP_ACCESS_KEY` is set
3. Restart API server with `uvicorn dashboard_api.app:app`

### Issue: "Invalid access key" on login
**Cause:** Key mismatch between frontend and backend

**Solution:**
1. Verify key entered matches `APP_ACCESS_KEY` in backend
2. Check for typos/whitespace
3. Regenerate and update both sides if needed

### Issue: Automatic logout / "Authentication failed"
**Cause:** Backend returned 401/403 (key invalid or expired)

**Solution:**
1. Check if `APP_ACCESS_KEY` was changed on backend
2. Login with current key
3. Clear browser localStorage if persisting: `localStorage.clear()`

### Issue: CORS errors in production
**Cause:** Frontend origin not allowed

**Solution:**
1. Set `CORS_ORIGINS` in backend `.env`
2. Example: `CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com`
3. Restart API server

## Alternative Authentication Options

If you need more advanced authentication in the future:

- **JWT with Users:** Individual user accounts with JWT tokens
- **OAuth:** Google/GitHub login integration
- **Session-based:** Traditional session cookies with Redis
- **API Gateway:** AWS API Gateway / Kong for enterprise auth

The current implementation can be upgraded to any of these without major changes.

## API Reference

### Authentication Dependency

```python
from dashboard_api.auth import require_app_access_key
from fastapi import Depends

@router.get("/my-endpoint")
async def my_endpoint(_: str = Depends(require_app_access_key)):
    return {"message": "Protected endpoint"}
```

### Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 401 | Missing access key | Provide X-App-Access-Key header |
| 403 | Invalid access key | Use correct key |
| 503 | Backend misconfigured | Set APP_ACCESS_KEY env var |

## Related Documentation

- [ADMIN_API.md](ADMIN_API.md) - Admin endpoint authentication
- [ADMIN_UI.md](ADMIN_UI.md) - Admin panel usage
- [README.md](../README.md) - General setup guide

---

**Last Updated:** 2026-01-29
