# Product Requirements Document: Free Hosting Deployment
## Small-Cap Growth Trading System

**Version:** 1.0
**Date:** 2026-01-18
**Status:** Draft
**Owner:** Development Team

---

## 1. Executive Summary

### 1.1 Objective
Deploy the Small-Cap Growth Trading System to free hosting platforms with the following architecture:
- **Backend (FastAPI):** Render free tier
- **Frontend (React/Vite):** Vercel free tier
- **Database:** Neon PostgreSQL free tier
- **Use Case:** Personal portfolio tracking (1 user)
- **Deployment:** Automated CI/CD from GitHub

### 1.2 Success Criteria
- [ ] Backend API accessible via HTTPS on Render
- [ ] Frontend accessible via HTTPS on Vercel with custom domain support
- [ ] PostgreSQL database successfully migrated from SQLite
- [ ] Auto-deployment working on git push to main branch
- [ ] All 4 trading strategies generating signals correctly
- [ ] Watchlist persistence working across deployments
- [ ] Price and fundamentals caching working with database backend
- [ ] Total deployment time: <2 hours for first deployment
- [ ] Zero monthly cost (within free tier limits)

---

## 2. Technical Architecture

### 2.1 Current Architecture
```
Local Development:
├── FastAPI backend (uvicorn, localhost:8000)
├── React frontend (Vite dev server, localhost:5173)
├── SQLite database (data/watchlist.db)
├── File-based cache (data/cache/, data/universe/)
└── Config files (config/settings.local.json - gitignored)
```

### 2.2 Target Production Architecture
```
Production:
├── Backend: Render Web Service
│   ├── FastAPI + Uvicorn (port $PORT)
│   ├── Auto-deploy from GitHub main branch
│   ├── Environment variables for secrets
│   └── Connected to Neon PostgreSQL
├── Frontend: Vercel
│   ├── Static React build (Vite)
│   ├── Auto-deploy from GitHub main branch
│   ├── Environment variable: VITE_API_BASE_URL
│   └── Global CDN distribution
├── Database: Neon PostgreSQL
│   ├── Serverless Postgres (auto-pause when idle)
│   ├── Connection pooling enabled
│   └── Tables: watchlist_entry, strategy_metrics
└── Cache Storage: Database-backed
    ├── Migrate file cache to PostgreSQL tables
    └── Alternative: Keep file cache (recreated on restart)
```

---

## 3. Platform Analysis & Constraints

### 3.1 Render (Backend) - Free Tier Limits

**Recommendation:** **Render is the best choice for this FastAPI project**

**Why Render:**
- Native FastAPI/ASGI support (no WSGI adapter needed)
- Automatic HTTPS/SSL certificates
- Environment variables management
- GitHub integration (auto-deploy)
- 750 hours/month (enough for personal use)
- 512MB RAM (sufficient for pandas/numpy operations)
- Persistent disk NOT available on free tier ⚠️

**Constraints:**
| Constraint | Impact | Mitigation |
|------------|--------|------------|
| **Sleeps after 15min inactivity** | First request takes 30-60s to wake | Acceptable for personal use; consider uptime ping service |
| **512MB RAM limit** | May struggle with large backtests (>500 symbols) | Limit universe scans to 50-100 symbols |
| **No persistent disk** | File cache (data/cache/, data/universe/) lost on restart | Migrate to PostgreSQL cache tables or accept recreation |
| **750 hours/month** | ~25 hours/day limit | More than enough for 1 user |
| **100GB bandwidth/month** | Each API call ~10-50KB | Can handle ~2M requests/month |

**Package Compatibility:**
✅ pandas, numpy, yfinance - All compatible
✅ fastapi, uvicorn, pydantic - Native support
✅ sqlmodel - Works with PostgreSQL
⚠️ Large dependencies (total ~200MB) - Within limits but slow cold starts

### 3.2 Vercel (Frontend) - Free Tier Limits

**Constraints:**
| Constraint | Impact | Mitigation |
|------------|--------|------------|
| **100GB bandwidth/month** | Each page load ~500KB-1MB | Can handle 100K+ page loads/month |
| **Unlimited builds** | Auto-deploy on every push | No issue |
| **32MB function size limit** | Not applicable (static site) | N/A |
| **10s function timeout** | Not applicable (static site) | N/A |

**Vite Build Size:**
- Estimated production build: 2-5MB (React + recharts + dependencies)
- Vercel limit: 100MB per deployment
- ✅ Well within limits

### 3.3 Neon PostgreSQL - Free Tier Limits

**Constraints:**
| Constraint | Impact | Mitigation |
|------------|--------|------------|
| **512MB storage** | Watchlist + cache tables | Limit cache to 30 days, auto-prune old data |
| **3GB data transfer/month** | Query bandwidth | More than enough for 1 user |
| **Auto-pause after 5min inactivity** | First query takes 1-3s to resume | Acceptable latency for personal use |
| **1 database** | All tables in single DB | No issue |
| **No backups on free tier** | Data loss risk | Export watchlist weekly via API endpoint |

**Estimated Storage Needs:**
- Watchlist entries: ~1KB per symbol × 100 symbols = 100KB
- Price cache: ~50KB per symbol × 100 symbols × 30 days = 150MB
- Fundamentals cache: ~10KB per symbol × 500 symbols = 5MB
- Strategy metrics: ~5MB
- **Total: ~160MB** ✅ Within 512MB limit

---

## 4. Database Migration Plan

### 4.1 SQLite to PostgreSQL Migration

**Current SQLite Schema:**
```python
# dashboard_api/watchlist.py
class WatchlistEntry(SQLModel, table=True):
    id: str = Field(primary_key=True)
    symbol: str
    status: str
    saved_at: datetime
    average_score: float
    final_scores: str  # JSON string
    aggregated_signal: Optional[str] = None
```

**Migration Tasks:**
1. ✅ No schema changes needed (SQLModel is PostgreSQL-compatible)
2. Update connection string from `sqlite:///data/watchlist.db` to PostgreSQL URL
3. Create migration script to export existing SQLite data (if any)
4. Add connection pooling for better performance
5. Update environment variable handling

**New Files Needed:**
- `database.py` - Centralized database configuration
- `alembic/` - Database migrations (optional, can use SQLModel.metadata.create_all())
- `.env.example` - Template for environment variables

### 4.2 Cache Storage Strategy

**Option A: Database-Backed Cache (Recommended for Render)**
```python
class PriceCache(SQLModel, table=True):
    id: int = Field(primary_key=True)
    symbol: str = Field(index=True)
    interval: str  # "1d", "1wk"
    data: str  # JSON-serialized OHLCV DataFrame
    fetched_at: datetime
    expires_at: datetime

class FundamentalsCache(SQLModel, table=True):
    id: int = Field(primary_key=True)
    symbol: str = Field(primary_key=True)
    data: str  # JSON-serialized fundamentals
    fetched_at: datetime
```

**Benefits:**
- Persists across Render restarts
- Respects TTL via `expires_at`
- Can query directly from PostgreSQL

**Drawbacks:**
- Uses database storage (but within 512MB limit)
- Slightly slower than file I/O (but with connection pooling, negligible)

**Option B: Accept Cache Loss (Simpler)**
- Keep file-based cache
- Cache recreated on Render restart (happens ~daily when app sleeps)
- Acceptable for personal use (first load after restart fetches fresh data)

**Recommendation:** Implement **Option A** for better UX, with auto-pruning of cache older than 30 days.

---

## 5. Deployment Workflow

### 5.1 Prerequisites Setup

**Step 1: GitHub Repository**
- [ ] Create private GitHub repo (or use existing)
- [ ] Push trading_system code to main branch
- [ ] Add `.gitignore` entries:
```gitignore
# Deployment
.env
.env.local
config/settings.local.json

# Build artifacts
dashboard_web/dist/
dashboard_web/node_modules/

# Data (already ignored)
data/
*.db
```

**Step 2: Create Neon Database**
1. Sign up at https://neon.tech
2. Create new project: "trading-system-db"
3. Copy connection string: `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`
4. Note down:
   - `DATABASE_URL` (full connection string)
   - `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` (for debugging)

**Step 3: Prepare Backend for Deployment**
- [ ] Create `database.py` with PostgreSQL configuration
- [ ] Update `dashboard_api/watchlist.py` to use new database module
- [ ] Create `render.yaml` for build configuration
- [ ] Create `requirements.txt` with pinned versions
- [ ] Add health check endpoint: `GET /health`

**Step 4: Prepare Frontend for Deployment**
- [ ] Update `dashboard_web/.env.production`:
```bash
VITE_API_BASE_URL=https://your-app.onrender.com
```
- [ ] Test production build locally: `npm run build && npm run preview`
- [ ] Verify API calls work with production URL

### 5.2 Backend Deployment (Render)

**Step 1: Create Render Web Service**
1. Go to https://render.com/dashboard
2. Click "New +" → "Web Service"
3. Connect GitHub repository
4. Configure:
   - **Name:** `trading-system-api`
   - **Region:** Oregon (closest free region)
   - **Branch:** `main`
   - **Root Directory:** `.` (or leave blank)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn dashboard_api.app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`

**Step 2: Add Environment Variables**
```bash
# Database
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require

# Alpha Vantage (optional)
TS_ALPHA_VANTAGE_KEY=your_alpha_vantage_key

# Email (optional)
TS_EMAIL_SMTP_HOST=smtp.gmail.com
TS_EMAIL_SMTP_PORT=587
TS_EMAIL_USERNAME=your_email@gmail.com
TS_EMAIL_PASSWORD=your_app_password

# App config
PYTHON_VERSION=3.11.0
```

**Step 3: Deploy**
- Click "Create Web Service"
- Render will automatically build and deploy
- Monitor logs for errors
- First deployment takes ~5-10 minutes

**Step 4: Verify**
- Visit `https://your-app.onrender.com/docs` (FastAPI interactive docs)
- Test health check: `https://your-app.onrender.com/health`
- Test symbol lookup: `https://your-app.onrender.com/api/symbols/AAPL`

### 5.3 Frontend Deployment (Vercel)

**Step 1: Create Vercel Project**
1. Go to https://vercel.com/new
2. Import GitHub repository
3. Configure:
   - **Framework Preset:** Vite
   - **Root Directory:** `dashboard_web`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`

**Step 2: Add Environment Variable**
```bash
VITE_API_BASE_URL=https://your-app.onrender.com
```

**Step 3: Deploy**
- Click "Deploy"
- Vercel automatically builds and deploys
- First deployment takes ~2-3 minutes

**Step 4: Verify**
- Visit `https://your-project.vercel.app`
- Check browser console for API connection
- Test symbol search, watchlist save, momentum pages

### 5.4 Auto-Deployment Setup

**Backend (Render):**
- ✅ Already configured via GitHub integration
- Every push to `main` branch triggers rebuild
- Can disable via Render dashboard → Settings → "Auto-Deploy"

**Frontend (Vercel):**
- ✅ Already configured via GitHub integration
- Every push to `main` branch triggers rebuild
- Can configure production/preview branches in Vercel dashboard

**Workflow:**
```bash
# Make changes locally
git add .
git commit -m "Add new feature"
git push origin main

# Automatic triggers:
# 1. Vercel starts building frontend (~2 min)
# 2. Render starts building backend (~5 min)
# 3. Both deploy automatically on success
```

---

## 6. Code Changes Required

### 6.1 Backend Changes

**File 1: `database.py` (NEW)**
```python
"""Database configuration for production deployment."""

from __future__ import annotations

import os
from typing import Iterable

from sqlmodel import Session, SQLModel, create_engine

# Use DATABASE_URL from environment, fallback to SQLite for local dev
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///data/watchlist.db"
)

# Neon PostgreSQL requires connection pooling
if DATABASE_URL.startswith("postgresql"):
    # Add connection pooling for PostgreSQL
    connect_args = {
        "connect_timeout": 10,
        "options": "-c timezone=utc",
    }
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before using
        connect_args=connect_args,
    )
else:
    # SQLite for local development
    engine = create_engine(DATABASE_URL, echo=False, future=True)


def init_db() -> None:
    """Create all tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterable[Session]:
    """Get database session."""
    with Session(engine) as session:
        yield session
```

**File 2: Update `dashboard_api/watchlist.py`**
```python
# OLD (remove these lines):
from pathlib import Path
from sqlmodel import create_engine

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "watchlist.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)

# NEW (replace with):
from dashboard_api.database import engine, init_db, get_session

# Remove duplicate init_db() and get_session() functions
```

**File 3: Update `dashboard_api/app.py`**
```python
# Add to startup event:
from dashboard_api.database import init_db

@app.on_event("startup")
def on_startup():
    """Initialize database on startup."""
    init_db()
    logger.info("Database initialized")

# Add health check endpoint:
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

**File 4: `render.yaml` (NEW)**
```yaml
# Render deployment configuration
services:
  - type: web
    name: trading-system-api
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn dashboard_api.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: DATABASE_URL
        sync: false  # Set manually in Render dashboard
```

**File 5: Update `requirements.txt`**
```txt
# Pin versions for reproducible builds
pandas==2.0.3
numpy==1.24.3
yfinance==0.2.28
requests==2.31.0
matplotlib==3.7.2
seaborn==0.12.2
jupyter==1.0.0
notebook==6.5.4
ipykernel==6.25.0
schedule==1.2.0
python-dateutil==2.8.2
pytest==7.4.0
fastapi==0.110.0
uvicorn[standard]==0.23.2
pydantic==2.6.0
sqlmodel==0.0.14
asgiref==3.8.0
gunicorn==21.2.0

# PostgreSQL driver (required for Neon)
psycopg2-binary==2.9.9

# Environment variable management
python-dotenv==1.0.0
```

**File 6: `.env.example` (NEW)**
```bash
# Copy this file to .env and fill in your values
# DO NOT commit .env to git

# Database (required)
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require

# Alpha Vantage API (optional)
TS_ALPHA_VANTAGE_KEY=your_key_here

# Email alerts (optional)
TS_EMAIL_SMTP_HOST=smtp.gmail.com
TS_EMAIL_SMTP_PORT=587
TS_EMAIL_USERNAME=your_email@gmail.com
TS_EMAIL_PASSWORD=your_app_password
```

### 6.2 Frontend Changes

**File 1: `dashboard_web/.env.production` (NEW)**
```bash
# Production environment variables
# This file can be committed (no secrets)
VITE_API_BASE_URL=https://your-app.onrender.com
```

**File 2: `dashboard_web/.env.development` (NEW)**
```bash
# Development environment variables
VITE_API_BASE_URL=http://localhost:8000
```

**File 3: Update `dashboard_web/src/config.ts` (if it doesn't exist, create it)**
```typescript
// API configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Feature flags
export const ENABLE_ANALYTICS = import.meta.env.PROD;
export const ENABLE_ERROR_TRACKING = import.meta.env.PROD;
```

**File 4: `dashboard_web/vercel.json` (NEW - optional, for custom routing)**
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

---

## 7. Migration Strategy

### 7.1 Database Migration Script

**File: `scripts/migrate_to_postgres.py` (NEW)**
```python
#!/usr/bin/env python3
"""
Migrate SQLite data to PostgreSQL.
Usage: python scripts/migrate_to_postgres.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, create_engine, select
from dashboard_api.watchlist import WatchlistEntry

# Source: SQLite
SQLITE_URL = "sqlite:///data/watchlist.db"
sqlite_engine = create_engine(SQLITE_URL, echo=False)

# Target: PostgreSQL from environment
POSTGRES_URL = os.getenv("DATABASE_URL")
if not POSTGRES_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

postgres_engine = create_engine(POSTGRES_URL, echo=False)

def migrate():
    """Migrate data from SQLite to PostgreSQL."""
    # Read from SQLite
    with Session(sqlite_engine) as sqlite_session:
        entries = sqlite_session.exec(select(WatchlistEntry)).all()
        print(f"Found {len(entries)} watchlist entries in SQLite")

    if not entries:
        print("No data to migrate")
        return

    # Write to PostgreSQL
    with Session(postgres_engine) as postgres_session:
        for entry in entries:
            postgres_session.add(entry)
        postgres_session.commit()
        print(f"Migrated {len(entries)} entries to PostgreSQL")

if __name__ == "__main__":
    migrate()
```

### 7.2 Migration Steps

1. **Before First Deployment:**
   ```bash
   # Local: Export existing SQLite data (if any)
   python scripts/export_watchlist.py > watchlist_backup.json
   ```

2. **After First Deployment:**
   ```bash
   # Set PostgreSQL URL locally
   export DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/neondb"

   # Run migration script
   python scripts/migrate_to_postgres.py
   ```

3. **Verify Migration:**
   ```bash
   # Test API locally with PostgreSQL
   uvicorn dashboard_api.app:app --reload

   # Check watchlist endpoint
   curl http://localhost:8000/api/watchlist
   ```

---

## 8. Cost Analysis

### 8.1 Free Tier Breakdown

| Service | Free Tier | Estimated Usage | Cost |
|---------|-----------|-----------------|------|
| **Render** | 750 hours/month, 512MB RAM | ~720 hours/month (always on) | $0 |
| **Vercel** | 100GB bandwidth | ~1GB/month (100 page loads) | $0 |
| **Neon PostgreSQL** | 512MB storage, 3GB transfer | ~200MB storage, 500MB transfer | $0 |
| **GitHub** | Unlimited public/private repos | 1 private repo | $0 |
| **Alpha Vantage** | 5 calls/min, 500/day | ~50 calls/day | $0 |
| **Total** | | | **$0/month** |

### 8.2 Paid Upgrade Paths (Future Consideration)

**If usage grows beyond personal:**

| Service | Paid Tier | Cost | When to Upgrade |
|---------|-----------|------|-----------------|
| **Render** | Starter ($7/mo) | $7 | Need persistent disk or more RAM |
| **Vercel** | Pro ($20/mo) | $20 | >100GB bandwidth or team features |
| **Neon PostgreSQL** | Launch ($19/mo) | $19 | >512MB storage or need backups |
| **Alpha Vantage** | Basic ($49/mo) | $49 | >500 calls/day |
| **Total** | | **$95/month** | For 10+ users or production scale |

**Recommendation:** Start free, upgrade Render first if app sleeps too frequently.

---

## 9. Performance Optimization

### 9.1 Render Sleep Mitigation

**Problem:** Render free tier sleeps after 15 minutes of inactivity. Wake-up takes 30-60 seconds.

**Solutions:**

**Option A: Uptime Monitoring (Recommended)**
- Use free service like UptimeRobot (https://uptimerobot.com/)
- Ping `/health` endpoint every 5 minutes
- Keeps Render instance awake during active hours
- Free tier: 50 monitors, 5-minute intervals

**Option B: Accept Sleep (Simpler)**
- First morning load takes 60s
- Subsequent loads are fast
- Acceptable for personal use

**Option C: Scheduled Wake-Up**
- Use GitHub Actions to ping API at 8 AM daily
- Free on GitHub
- Example workflow:
```yaml
# .github/workflows/wake-api.yml
name: Wake API
on:
  schedule:
    - cron: '0 8 * * *'  # 8 AM UTC daily
jobs:
  wake:
    runs-on: ubuntu-latest
    steps:
      - run: curl https://your-app.onrender.com/health
```

**Recommendation:** Implement **Option A** (UptimeRobot) for best UX.

### 9.2 Database Connection Pooling

Already configured in `database.py`:
- `pool_size=5` - Max 5 active connections
- `max_overflow=10` - Allow 10 additional connections under load
- `pool_pre_ping=True` - Verify connections before use (important for Neon auto-pause)

### 9.3 Frontend Performance

**Optimizations:**
- ✅ Vite automatically code-splits and minifies
- ✅ Vercel serves from global CDN
- ✅ Recharts lazy-loaded only on chart pages

**Additional:**
- Add loading skeletons for slow API calls
- Cache API responses in localStorage (5-minute TTL)
- Add service worker for offline support (optional)

---

## 10. Monitoring & Maintenance

### 10.1 Health Checks

**Backend Health Check:**
```bash
GET https://your-app.onrender.com/health

Response:
{
  "status": "healthy",
  "timestamp": "2026-01-18T10:30:00Z"
}
```

**Database Health Check:**
Add to `/health` endpoint:
```python
@app.get("/health")
def health_check():
    # Test database connection
    try:
        with Session(engine) as session:
            session.exec(select(WatchlistEntry).limit(1))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
    }
```

### 10.2 Logging

**Render Logs:**
- View in Render dashboard → Logs tab
- Real-time streaming
- 7-day retention on free tier

**Important Log Patterns:**
```python
# In dashboard_api/app.py
import logging

logger = logging.getLogger("trading_system.api")

# Log API requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Status: {response.status_code}")
    return response
```

### 10.3 Error Tracking

**Option A: Sentry (Free Tier)**
- 5,000 events/month free
- Real-time error notifications
- Performance monitoring

**Setup:**
```bash
pip install sentry-sdk[fastapi]
```

```python
# In dashboard_api/app.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment="production",
    traces_sample_rate=0.1,
)
```

**Option B: Simple Email Alerts**
- Use existing `automation/emailer.py`
- Send email on 500 errors

**Recommendation:** Start without error tracking, add Sentry if needed.

### 10.4 Database Maintenance

**Weekly Backup (Manual):**
```bash
# Export watchlist via API
curl https://your-app.onrender.com/api/watchlist > watchlist_backup_$(date +%Y%m%d).json
```

**Auto-Prune Old Cache (Add to Backend):**
```python
# In dashboard_api/app.py startup event
@app.on_event("startup")
async def prune_old_cache():
    """Delete cache entries older than 30 days."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=30)

    with Session(engine) as session:
        # Add pruning logic for cache tables
        pass
```

---

## 11. Security Considerations

### 11.1 Environment Variables

**Never commit:**
- `DATABASE_URL`
- `TS_ALPHA_VANTAGE_KEY`
- `TS_EMAIL_PASSWORD`
- Any API keys or credentials

**Use:**
- Render dashboard → Environment → Environment Variables
- Vercel dashboard → Settings → Environment Variables
- `.env.example` committed to repo as template
- `.env` added to `.gitignore`

### 11.2 API Security

**Current Status:**
- ❌ No authentication (public API)
- ❌ No rate limiting
- ❌ No CORS restrictions

**For Personal Use (Acceptable):**
- Keep URLs private (don't share publicly)
- Monitor Render logs for suspicious activity
- Alpha Vantage key has rate limits (5 calls/min)

**For Future Production (Recommended):**
```python
# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-project.vercel.app"],  # Only your frontend
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Add rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.get("/api/symbols/{symbol}")
@limiter.limit("10/minute")  # Max 10 requests per minute
def get_symbol(symbol: str):
    ...
```

### 11.3 Database Security

**Current:**
- ✅ Neon uses SSL by default (`sslmode=require`)
- ✅ Connection string in environment variable
- ❌ No connection encryption beyond SSL

**Best Practices:**
- Don't log `DATABASE_URL` in code
- Use connection pooling to limit connections
- Neon auto-pauses when idle (reduces exposure)

---

## 12. Testing Strategy

### 12.1 Pre-Deployment Testing

**Backend:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set test database URL
export DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/neondb"

# Run tests
pytest tests/

# Test API locally with PostgreSQL
uvicorn dashboard_api.app:app --reload

# Verify endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/symbols/AAPL
```

**Frontend:**
```bash
cd dashboard_web

# Install dependencies
npm install

# Update .env.development
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.development

# Test dev build
npm run dev

# Test production build
npm run build
npm run preview
```

### 12.2 Post-Deployment Testing

**Checklist:**
- [ ] Backend `/health` returns 200
- [ ] Backend `/docs` loads (FastAPI Swagger UI)
- [ ] Frontend loads without console errors
- [ ] Symbol search works (try AAPL)
- [ ] Strategy cards render with confidence scores
- [ ] Watchlist save/load works
- [ ] Russell/SP500 momentum pages load
- [ ] Price charts render correctly
- [ ] No CORS errors in browser console

**Test API Endpoints:**
```bash
# Health check
curl https://your-app.onrender.com/health

# Symbol analysis
curl https://your-app.onrender.com/api/symbols/AAPL

# Watchlist
curl https://your-app.onrender.com/api/watchlist

# Momentum
curl https://your-app.onrender.com/api/russell/momentum?timeframe=week&limit=10
```

---

## 13. Deployment Timeline

### 13.1 Estimated Timeline (First Deployment)

| Phase | Task | Estimated Time |
|-------|------|----------------|
| **1. Preparation** | Create GitHub repo, push code | 15 min |
| | Create Neon database | 5 min |
| | Code changes (database.py, render.yaml, etc.) | 30 min |
| | Local testing with PostgreSQL | 15 min |
| **2. Backend Deployment** | Create Render service | 10 min |
| | Configure environment variables | 5 min |
| | Wait for first build | 5-10 min |
| | Test API endpoints | 10 min |
| **3. Frontend Deployment** | Create Vercel project | 5 min |
| | Configure environment variables | 5 min |
| | Wait for first build | 2-3 min |
| | Test frontend | 10 min |
| **4. Verification** | End-to-end testing | 15 min |
| | Fix any issues | 15 min |
| **Total** | | **~2 hours** |

### 13.2 Subsequent Deployments (Auto)

After initial setup:
```bash
git add .
git commit -m "Update feature"
git push origin main

# Auto-deploy:
# - Vercel: ~2 minutes
# - Render: ~5 minutes
# Total: ~7 minutes, zero manual work
```

---

## 14. Rollback Plan

### 14.1 Rollback Strategies

**Render (Backend):**
- Option 1: Redeploy previous commit from Render dashboard
- Option 2: `git revert` and push (triggers auto-deploy)
- Option 3: Manual deploy from specific commit

**Vercel (Frontend):**
- Instant rollback from Vercel dashboard → Deployments → "Promote to Production"
- Reverts to previous deployment in seconds

**Database:**
- ⚠️ No automatic backups on Neon free tier
- Must manually export data before risky changes
- Keep `watchlist_backup.json` in safe location

### 14.2 Emergency Procedures

**If API is down:**
1. Check Render logs for errors
2. Check Neon database status (may be paused)
3. Restart Render service from dashboard
4. If persist, rollback to last working deployment

**If Frontend is broken:**
1. Rollback deployment in Vercel (instant)
2. Clear browser cache
3. Check API endpoint is accessible

**If Database connection fails:**
1. Verify `DATABASE_URL` in Render environment variables
2. Check Neon database status (auto-pauses after 5min)
3. Test connection locally: `psql $DATABASE_URL`
4. Worst case: Recreate database and restore from backup

---

## 15. Future Enhancements

### 15.1 Phase 2 (Optional)

**After successful deployment:**
- [ ] Add authentication (Auth0, Supabase Auth, or simple JWT)
- [ ] Implement rate limiting on API
- [ ] Add CORS restrictions to allow only Vercel frontend
- [ ] Set up UptimeRobot to prevent Render sleep
- [ ] Add Sentry error tracking
- [ ] Implement database backups (export to GitHub Gist nightly)

### 15.2 Phase 3 (Scaling)

**If usage grows:**
- [ ] Upgrade Render to Starter plan ($7/mo) for persistent disk
- [ ] Implement Redis caching (Upstash free tier)
- [ ] Add CDN for API responses (Cloudflare Workers free tier)
- [ ] Move to paid PostgreSQL with backups
- [ ] Add analytics (Plausible Analytics, privacy-focused)

---

## 16. Success Metrics

### 16.1 Deployment Success Criteria

**Must Have (Blocker):**
- [ ] Backend API accessible via HTTPS
- [ ] Frontend loads without errors
- [ ] Database connection working
- [ ] Watchlist save/load working
- [ ] At least one strategy generating signals

**Should Have (Important):**
- [ ] All 4 strategies working
- [ ] Price cache persisting
- [ ] Auto-deployment working
- [ ] Health check returning 200

**Nice to Have (Enhancement):**
- [ ] Custom domain on Vercel
- [ ] UptimeRobot monitoring
- [ ] Error tracking configured
- [ ] Database backups automated

### 16.2 Performance Benchmarks

**Target Performance:**
- Homepage load time: <2 seconds
- Symbol search response: <3 seconds (first load after sleep)
- Symbol search response: <500ms (warm instance)
- Watchlist save: <200ms
- Database query: <100ms (warm)

**Monitoring:**
- Use browser DevTools Network tab
- Render logs show request duration
- Add timing logs in backend: `logger.info(f"Query took {elapsed}ms")`

---

## 17. Documentation & Handoff

### 17.1 Documentation Updates Needed

**Update these files after deployment:**

1. **README.md**
   - Add "Live Demo" section with Vercel URL
   - Update installation instructions for production
   - Add PostgreSQL migration guide

2. **claude.md**
   - Add deployment section
   - Document environment variables
   - Add troubleshooting for Render/Vercel

3. **New: DEPLOYMENT.md**
   - Step-by-step deployment guide
   - Screenshots of Render/Vercel configuration
   - Common issues and solutions

### 17.2 Knowledge Transfer

**Key Information to Document:**

1. **URLs:**
   - Backend: `https://your-app.onrender.com`
   - Frontend: `https://your-project.vercel.app`
   - Database: `ep-xxx.neon.tech`

2. **Credentials Location:**
   - Render: Environment variables in dashboard
   - Vercel: Environment variables in dashboard
   - Neon: Connection string in password manager

3. **Monitoring:**
   - Render logs: Dashboard → Logs
   - Vercel analytics: Dashboard → Analytics
   - Neon metrics: Dashboard → Metrics

---

## 18. Appendix

### 18.1 Useful Commands

```bash
# Backend Development
uvicorn dashboard_api.app:app --reload --port 8000

# Frontend Development
cd dashboard_web && npm run dev

# Production Test (Local)
export DATABASE_URL="postgresql://..."
uvicorn dashboard_api.app:app --host 0.0.0.0 --port 8000

# Database Connection Test
psql $DATABASE_URL -c "SELECT COUNT(*) FROM watchlistentry;"

# Deploy Manually (if auto-deploy disabled)
git push render main  # If Render git remote configured

# View Logs
# Render: Dashboard → Logs
# Vercel: Dashboard → Deployments → [deployment] → Build Logs
```

### 18.2 Troubleshooting Reference

| Issue | Symptom | Solution |
|-------|---------|----------|
| Render build fails | "Failed to build" | Check requirements.txt versions, view logs |
| Database connection error | "could not connect to server" | Verify DATABASE_URL, check Neon status |
| Frontend CORS error | "Access-Control-Allow-Origin" | Update VITE_API_BASE_URL, check backend CORS |
| Slow first load | 30-60s response time | Normal on free tier (cold start), use UptimeRobot |
| 500 error on API | "Internal Server Error" | Check Render logs, verify database connection |
| Module not found | "ModuleNotFoundError" | Check requirements.txt, rebuild on Render |

### 18.3 Contact & Support

**Platform Support:**
- Render: https://render.com/docs, support via dashboard
- Vercel: https://vercel.com/docs, support@vercel.com
- Neon: https://neon.tech/docs, support@neon.tech

**Community:**
- Render Discord: https://render.com/discord
- Vercel Discord: https://vercel.com/discord

---

## 19. Approval & Sign-off

### 19.1 Stakeholder Review

- [ ] Technical review completed
- [ ] Security review completed (environment variables, no secrets in code)
- [ ] Cost analysis approved (free tier acceptable)
- [ ] Timeline approved (~2 hours for first deployment)

### 19.2 Go/No-Go Decision

**Go Criteria:**
- [x] All code changes documented
- [x] Migration plan defined
- [x] Rollback plan defined
- [x] Free tier limits understood and acceptable
- [x] Performance expectations set (sleep after 15min acceptable)

**Decision:** ✅ **GO** - Proceed with deployment

---

**Document Version History:**
- v1.0 (2026-01-18): Initial PRD created based on project analysis and user requirements

**Next Steps:**
1. Review this PRD
2. Create GitHub repository (if not exists)
3. Begin code changes (Section 6)
4. Follow deployment workflow (Section 5)
5. Test thoroughly (Section 12)
6. Monitor and maintain (Section 10)
