# Complete Deployment Guide
## Automated Setup Using CLI Tools

This guide will walk you through deploying your Trading System using maximum automation with CLI tools.

**Estimated Time:** 30-45 minutes
**Cost:** $0/month (all free tiers)

---

## Table of Contents

1. [Prerequisites Installation](#1-prerequisites-installation)
2. [Quick Start (Automated)](#2-quick-start-automated)
3. [Manual Step-by-Step](#3-manual-step-by-step)
4. [Configuration & Testing](#4-configuration--testing)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Prerequisites Installation

### 1.1 Install Required CLI Tools

Open PowerShell as Administrator and run:

```powershell
# Install GitHub CLI
winget install GitHub.cli

# Install Node.js (required for Vercel CLI)
winget install OpenJS.NodeJS

# Install Vercel CLI (after Node.js is installed)
npm install -g vercel

# Verify installations
gh --version
node --version
vercel --version
```

**Expected Output:**
```
gh version 2.x.x
v20.x.x
Vercel CLI 33.x.x
```

### 1.2 Create Required Accounts

If you don't have accounts yet, sign up for:

1. **GitHub:** https://github.com/join (Free)
2. **Render:** https://render.com/register (Free tier)
3. **Vercel:** https://vercel.com/signup (Free tier)
4. **Neon:** https://console.neon.tech/sign_in (Free tier)

**Important:** Use the same email for all services for easier management.

---

## 2. Quick Start (Automated)

### 2.1 Run the Automated Setup Script

From your project root (`c:\projects\trading_system`):

```powershell
# First, do a dry run to see what will happen
.\scripts\deploy_setup.ps1 -DryRun

# If everything looks good, run the actual deployment
.\scripts\deploy_setup.ps1
```

The script will:
1. ✓ Check all prerequisites
2. ✓ Login to GitHub CLI and Vercel CLI
3. ✓ Create `.gitignore` file
4. ✓ Initialize Git repository
5. ✓ Create GitHub repository (will prompt for name)
6. ✓ Push code to GitHub
7. ✓ Show instructions for Render setup
8. ✓ Deploy frontend to Vercel

### 2.2 Follow the Script Prompts

The script will pause at certain points and ask for input:

**Prompt 1: GitHub Repository Name**
```
Enter GitHub repository name (e.g., trading-system):
```
Enter: `trading-system` (or your preferred name)

**Prompt 2: GitHub CLI Login**
- Browser will open
- Login to GitHub
- Authorize GitHub CLI

**Prompt 3: Vercel CLI Login**
- Browser will open
- Login to Vercel
- Authorize Vercel CLI

**Prompt 4: Render Manual Setup**
- Script will show instructions
- Press Enter after completing manual steps

### 2.3 Complete Manual Steps

After the automated script, you'll need to:

1. **Create Neon Database** (5 minutes)
2. **Configure Render** (5 minutes)
3. **Update Vercel Environment Variables** (2 minutes)

See [Section 3](#3-manual-step-by-step) for detailed instructions.

---

## 3. Manual Step-by-Step

If the automated script doesn't work or you prefer manual control:

### 3.1 GitHub Setup

#### Option A: Using GitHub CLI (Fastest)

```powershell
# Login to GitHub CLI
gh auth login
# Select: GitHub.com
# Select: HTTPS
# Select: Login with a web browser
# Copy the one-time code and press Enter

# Create repository
gh repo create trading-system --private --source=. --remote=origin

# Initial commit and push
git add .
git commit -m "Initial commit - Trading System"
git branch -M main
git push -u origin main

# Verify
gh repo view --web
```

#### Option B: Using Git + Web Browser

```powershell
# 1. Go to: https://github.com/new
# 2. Repository name: trading-system
# 3. Private repository: ✓ Checked
# 4. Click "Create repository"

# 5. In your terminal:
git init
git add .
git commit -m "Initial commit - Trading System"
git branch -M main

# 6. Add remote (replace YOUR_USERNAME):
git remote add origin https://github.com/YOUR_USERNAME/trading-system.git
git push -u origin main
```

### 3.2 Neon PostgreSQL Setup

**Step 1: Create Project**

1. Go to: https://console.neon.tech/app/projects
2. Click **"New Project"**
3. Configure:
   - **Project name:** `trading-system-db`
   - **PostgreSQL version:** 16 (latest)
   - **Region:** US East (Ohio) - closest free region
   - Click **"Create Project"**

**Step 2: Get Connection String**

1. On the project dashboard, find **"Connection Details"**
2. Click **"Connection string"** tab
3. Copy the connection string that looks like:
   ```
   postgresql://username:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. **Save this** - you'll need it multiple times

**Step 3: Verify Connection (Optional)**

```powershell
# Install PostgreSQL client (if you want to test)
winget install PostgreSQL.PostgreSQL

# Test connection (replace with your URL)
psql "postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require" -c "SELECT version();"
```

### 3.3 Render Backend Setup

**Step 1: Create Web Service**

1. Go to: https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Click **"Connect account"** → Select **GitHub**
4. Authorize Render to access your GitHub
5. Find your repository: `trading-system`
6. Click **"Connect"**

**Step 2: Configure Service**

Fill in the form:

| Field | Value |
|-------|-------|
| **Name** | `trading-system-api` |
| **Region** | Oregon (US West) |
| **Branch** | `main` |
| **Root Directory** | (leave blank) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn dashboard_api.app:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` |

**Step 3: Add Environment Variables**

Scroll down to **"Environment Variables"** section, click **"Add Environment Variable"**:

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.11.0` |
| `DATABASE_URL` | (paste your Neon connection string) |
| `TS_ALPHA_VANTAGE_KEY` | (your Alpha Vantage API key - optional) |

**Example:**
```
Key: DATABASE_URL
Value: postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

**Step 4: Deploy**

1. Click **"Create Web Service"**
2. Render will start building (takes 5-10 minutes)
3. Monitor logs in the **"Logs"** tab
4. Wait for: `Application startup complete` message

**Step 5: Get Your API URL**

Once deployed, your API URL will be:
```
https://trading-system-api.onrender.com
```

Copy this URL - you'll need it for Vercel.

**Step 6: Verify Backend**

Test your API:

```powershell
# Test health endpoint
curl https://trading-system-api.onrender.com/health

# Expected response:
# {"status":"healthy","timestamp":"2026-01-18T..."}

# Open interactive API docs in browser:
start https://trading-system-api.onrender.com/docs
```

### 3.4 Vercel Frontend Setup

#### Option A: Using Vercel CLI (Fastest)

```powershell
# Navigate to frontend directory
cd dashboard_web

# Login to Vercel
vercel login
# Browser will open - login and authorize

# Deploy to production
vercel --prod

# Follow prompts:
# ? Set up and deploy "~\dashboard_web"? [Y/n] y
# ? Which scope do you want to deploy to? (select your account)
# ? Link to existing project? [y/N] n
# ? What's your project's name? trading-system-dashboard
# ? In which directory is your code located? ./
# ? Want to override the settings? [y/N] n

# Vercel will build and deploy (takes 2-3 minutes)
```

**Expected Output:**
```
✓ Production: https://trading-system-dashboard.vercel.app [2m]
```

#### Option B: Using Vercel Web Dashboard

1. Go to: https://vercel.com/new
2. Click **"Import Git Repository"**
3. Click **"Continue with GitHub"**
4. Find your repository: `trading-system`
5. Click **"Import"**

Configure project:

| Field | Value |
|-------|-------|
| **Project Name** | `trading-system-dashboard` |
| **Framework Preset** | `Vite` |
| **Root Directory** | `dashboard_web` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

6. Click **"Deploy"**
7. Wait for deployment (2-3 minutes)

**Step 2: Add Environment Variable**

1. Go to: Project → **Settings** → **Environment Variables**
2. Add variable:
   - **Key:** `VITE_API_BASE_URL`
   - **Value:** `https://trading-system-api.onrender.com` (your Render URL)
   - **Environment:** Production, Preview, Development (check all)
3. Click **"Save"**

**Step 3: Redeploy**

Since we added environment variables, we need to redeploy:

```powershell
# Using CLI
cd dashboard_web
vercel --prod

# Or in web dashboard:
# Go to Deployments → Click "..." → Redeploy
```

**Step 4: Get Your Frontend URL**

Your frontend will be at:
```
https://trading-system-dashboard.vercel.app
```

Or check in terminal/dashboard for the exact URL.

### 3.5 Verify Full Deployment

**Test the complete system:**

1. **Open Frontend:**
   ```powershell
   start https://trading-system-dashboard.vercel.app
   ```

2. **Test Symbol Search:**
   - Type "AAPL" in search box
   - Should load Apple stock data
   - Check browser console (F12) for errors

3. **Test Watchlist:**
   - Search for a symbol
   - Click "Save to Watchlist"
   - Go to Watchlist page
   - Should see saved symbol

4. **Test Strategies:**
   - View a symbol detail page
   - Should see 4 strategy cards (CAN SLIM, Dan Zanger, Trend, Livermore)
   - Each should show confidence scores

**If everything works:** ✅ Deployment Complete!

---

## 4. Configuration & Testing

### 4.1 Enable Auto-Deployment

**Good news:** Auto-deployment is already enabled!

Both Render and Vercel automatically watch your GitHub repository.

**Test auto-deployment:**

```powershell
# Make a small change
echo "# Auto-deploy test" >> README.md

# Commit and push
git add README.md
git commit -m "Test auto-deploy"
git push origin main

# Watch deployments:
# Render: https://dashboard.render.com/
# Vercel: https://vercel.com/dashboard
```

**Expected:**
- Render starts building within 30 seconds
- Vercel starts building within 10 seconds
- Both complete automatically

### 4.2 Set Up Custom Domain (Optional)

**For Vercel (Frontend):**

1. Go to: Project → **Settings** → **Domains**
2. Add your domain (e.g., `trading.yourdomain.com`)
3. Add DNS records as shown by Vercel
4. Wait for SSL certificate (automatic)

**For Render (Backend):**

1. Go to: Service → **Settings** → **Custom Domain**
2. Add your domain (e.g., `api.yourdomain.com`)
3. Add DNS CNAME record pointing to Render
4. Wait for SSL certificate (automatic)

### 4.3 Configure Secrets (Optional)

**Add Alpha Vantage API Key:**

1. Get free key: https://www.alphavantage.co/support/#api-key
2. In Render dashboard:
   - Go to: Service → **Environment**
   - Click **"Add Environment Variable"**
   - Key: `TS_ALPHA_VANTAGE_KEY`
   - Value: (your API key)
   - Click **"Save Changes"**
3. Render will redeploy automatically

**Add Email Settings (Optional):**

For portfolio alerts:

```
TS_EMAIL_SMTP_HOST=smtp.gmail.com
TS_EMAIL_SMTP_PORT=587
TS_EMAIL_USERNAME=your_email@gmail.com
TS_EMAIL_PASSWORD=your_app_password
```

**Note:** For Gmail, create an "App Password" at: https://myaccount.google.com/apppasswords

### 4.4 Set Up Uptime Monitoring (Prevent Sleep)

Render free tier sleeps after 15 minutes of inactivity. Prevent this:

**Using UptimeRobot (Free):**

1. Go to: https://uptimerobot.com/
2. Sign up (free)
3. Click **"Add New Monitor"**
4. Configure:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** Trading System API
   - **URL:** `https://trading-system-api.onrender.com/health`
   - **Monitoring Interval:** 5 minutes
5. Click **"Create Monitor"**

**Using GitHub Actions (Alternative):**

Create `.github/workflows/keep-alive.yml`:

```yaml
name: Keep Render Alive
on:
  schedule:
    - cron: '*/10 * * * *'  # Every 10 minutes
  workflow_dispatch:

jobs:
  wake:
    runs-on: ubuntu-latest
    steps:
      - name: Ping API
        run: |
          curl https://trading-system-api.onrender.com/health
          echo "API pinged successfully"
```

Commit and push this file - GitHub will run it automatically.

---

## 5. Troubleshooting

### 5.1 Common Issues

#### Issue: GitHub CLI Authentication Fails

**Symptom:**
```
error: failed to run gh: failed to authenticate
```

**Solution:**
```powershell
# Logout and login again
gh auth logout
gh auth login

# Select: GitHub.com, HTTPS, Login with browser
```

#### Issue: Vercel CLI Deployment Fails

**Symptom:**
```
Error: No Space Left on Device
```

**Solution:**
```powershell
# Clear Vercel cache
vercel --force

# Or redeploy
vercel --prod --force
```

#### Issue: Render Build Fails - Module Not Found

**Symptom:**
```
ModuleNotFoundError: No module named 'psycopg2'
```

**Solution:**
1. Check `requirements.txt` includes `psycopg2-binary==2.9.9`
2. Commit and push:
   ```powershell
   git add requirements.txt
   git commit -m "Add psycopg2-binary"
   git push origin main
   ```

#### Issue: Frontend Shows CORS Error

**Symptom:**
```
Access to XMLHttpRequest at 'https://...' from origin 'https://...' has been blocked by CORS policy
```

**Solution:**
1. Verify `VITE_API_BASE_URL` is set correctly in Vercel
2. Check Render API logs for errors
3. Ensure Render service is running (not sleeping)

#### Issue: Database Connection Error

**Symptom:**
```
could not connect to server: Connection timed out
```

**Solution:**
1. Check Neon database is active (dashboard)
2. Verify `DATABASE_URL` in Render environment variables
3. Ensure URL includes `?sslmode=require`
4. Try pinging from Render shell:
   ```bash
   # In Render shell
   psql $DATABASE_URL -c "SELECT 1;"
   ```

#### Issue: Render App Sleeping Too Much

**Symptom:**
First request takes 60 seconds every time

**Solution:**
- Set up UptimeRobot (see section 4.4)
- Or upgrade to Render Starter plan ($7/mo) to keep awake

### 5.2 Debugging Commands

**Check Git status:**
```powershell
git status
git remote -v
git log --oneline -5
```

**Check GitHub CLI:**
```powershell
gh auth status
gh repo view
gh repo view --web
```

**Check Vercel deployments:**
```powershell
vercel list
vercel inspect https://your-deployment-url.vercel.app
vercel logs
```

**Test database connection:**
```powershell
# Set environment variable
$env:DATABASE_URL = "postgresql://..."

# Test with Python
python -c "from sqlmodel import create_engine; engine = create_engine('$env:DATABASE_URL'); print('Connected!')"
```

**View Render logs:**
```powershell
# In browser
start https://dashboard.render.com/

# Navigate to your service → Logs tab
# Or use Render CLI (if installed):
render services logs trading-system-api
```

### 5.3 Reset and Start Over

If something goes completely wrong:

**Reset GitHub:**
```powershell
# Delete remote repository
gh repo delete YOUR_USERNAME/trading-system --yes

# Remove local .git folder
Remove-Item -Recurse -Force .git

# Start fresh
git init
```

**Reset Render:**
1. Go to: https://dashboard.render.com/
2. Select your service
3. Click **"Settings"** → **"Delete Service"**
4. Create new service following section 3.3

**Reset Vercel:**
```powershell
# Delete project
vercel remove trading-system-dashboard

# Or in dashboard:
# Project → Settings → General → Delete Project
```

---

## 6. Quick Reference

### 6.1 Important URLs

| Service | Purpose | URL |
|---------|---------|-----|
| **GitHub Repo** | Source code | https://github.com/YOUR_USERNAME/trading-system |
| **Render Dashboard** | Backend monitoring | https://dashboard.render.com/ |
| **Render API** | Backend endpoint | https://trading-system-api.onrender.com |
| **Render Docs** | API documentation | https://trading-system-api.onrender.com/docs |
| **Vercel Dashboard** | Frontend monitoring | https://vercel.com/dashboard |
| **Vercel App** | Frontend app | https://trading-system-dashboard.vercel.app |
| **Neon Console** | Database management | https://console.neon.tech/ |
| **UptimeRobot** | Monitoring | https://uptimerobot.com/dashboard |

### 6.2 CLI Commands Cheat Sheet

```powershell
# GitHub
gh auth login                          # Login to GitHub
gh repo create NAME --private          # Create repo
gh repo view --web                     # Open repo in browser

# Git
git status                             # Check status
git add .                              # Stage all changes
git commit -m "message"                # Commit changes
git push origin main                   # Push to GitHub

# Vercel
vercel login                           # Login to Vercel
vercel --prod                          # Deploy to production
vercel list                            # List deployments
vercel logs                            # View logs

# Testing
curl https://your-api.onrender.com/health           # Test backend
start https://your-app.vercel.app                   # Open frontend
psql $DATABASE_URL -c "SELECT version();"           # Test database
```

### 6.3 Environment Variables Reference

**Render (Backend):**
```
PYTHON_VERSION=3.11.0
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
TS_ALPHA_VANTAGE_KEY=your_api_key
TS_EMAIL_SMTP_HOST=smtp.gmail.com
TS_EMAIL_SMTP_PORT=587
TS_EMAIL_USERNAME=your_email@gmail.com
TS_EMAIL_PASSWORD=your_app_password
```

**Vercel (Frontend):**
```
VITE_API_BASE_URL=https://trading-system-api.onrender.com
```

---

## 7. Next Steps After Deployment

### 7.1 Immediate Tasks

- [ ] Test all features (search, watchlist, strategies, momentum)
- [ ] Set up UptimeRobot monitoring
- [ ] Bookmark dashboard URLs
- [ ] Save database connection string securely
- [ ] Export initial watchlist as backup

### 7.2 Ongoing Maintenance

**Weekly:**
- Check Render logs for errors
- Verify database size (stay under 512MB)
- Export watchlist backup

**Monthly:**
- Review Render/Vercel usage (ensure within free tier)
- Update dependencies if needed
- Check for new features in deployment_prd.md

**As Needed:**
- Add new symbols to watchlist
- Run backtests via CLI (locally)
- Update Alpha Vantage key if expired

### 7.3 Future Enhancements

Consider implementing:
- Custom domain names
- Authentication/login system
- Email alerts for portfolio changes
- Automated backup to GitHub Gist
- Upgrade to paid tiers for better performance

---

## 8. Getting Help

### 8.1 Documentation

- **This project:** [README.md](README.md), [deployment_prd.md](deployment_prd.md), [claude.md](claude.md)
- **Render:** https://render.com/docs
- **Vercel:** https://vercel.com/docs
- **Neon:** https://neon.tech/docs
- **GitHub CLI:** https://cli.github.com/manual/

### 8.2 Support

- **Render:** https://render.com/docs/support (chat in dashboard)
- **Vercel:** https://vercel.com/support
- **Neon:** support@neon.tech
- **GitHub:** https://support.github.com/

### 8.3 Community

- **Render Community:** https://community.render.com/
- **Vercel Discord:** https://vercel.com/discord
- **GitHub Discussions:** https://github.com/community

---

**Deployment Complete! 🎉**

Your Trading System is now live on:
- **Frontend:** https://trading-system-dashboard.vercel.app
- **Backend:** https://trading-system-api.onrender.com

Auto-deployment is enabled. Every `git push` will automatically update both services.

For questions or issues, refer to the [Troubleshooting](#5-troubleshooting) section.
