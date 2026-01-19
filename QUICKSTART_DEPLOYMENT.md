# Quick Start: Deploy in 30 Minutes

This is the **fastest path** to get your Trading System deployed online for free.

**Time Required:** ~30 minutes
**Cost:** $0/month
**Result:** Live web app accessible from anywhere

---

## Before You Start

You need:
- [x] Windows PC with PowerShell
- [x] Trading System code (this repository)
- [ ] 4 free accounts (GitHub, Render, Vercel, Neon) - we'll create these

---

## Step 1: Install CLI Tools (5 minutes)

Open PowerShell **as Administrator** and run:

```powershell
# Navigate to your project
cd c:\projects\trading_system

# Run installer
.\scripts\install_cli_tools.ps1
```

The script will install:
- ✓ Git
- ✓ GitHub CLI
- ✓ Node.js
- ✓ Vercel CLI

**After installation completes:**
1. Close PowerShell
2. Open a **new** PowerShell window (to refresh PATH)

---

## Step 2: Create Free Accounts (10 minutes)

Open these links and sign up (use the same email for all):

1. **GitHub:** https://github.com/join
   - Choose username
   - Verify email
   - ✓ Done

2. **Render:** https://render.com/register
   - Sign up with GitHub (easiest)
   - ✓ Done

3. **Vercel:** https://vercel.com/signup
   - Sign up with GitHub (easiest)
   - ✓ Done

4. **Neon:** https://console.neon.tech/sign_in
   - Sign up with GitHub (easiest)
   - ✓ Done

**Tip:** Keep these browser tabs open - you'll need them.

---

## Step 3: Create Database (3 minutes)

In the **Neon** tab:

1. Click **"New Project"**
2. Name: `trading-system-db`
3. Click **"Create Project"**
4. Copy the **connection string** (looks like `postgresql://username:password@...`)
5. **Save it in Notepad** - you'll need it twice

---

## Step 4: Automated Deployment (10 minutes)

Back in PowerShell:

```powershell
# Navigate to project (if not already there)
cd c:\projects\trading_system

# Run automated deployment
.\scripts\deploy_setup.ps1
```

**The script will prompt you for:**

### Prompt 1: GitHub Login
- Browser opens automatically
- Login to GitHub
- Click **"Authorize"**
- Return to PowerShell

### Prompt 2: Repository Name
```
Enter GitHub repository name: trading-system
```
Just press **Enter** (uses default name)

### Prompt 3: Vercel Login
- Browser opens automatically
- Login to Vercel
- Click **"Authorize"**
- Return to PowerShell

### Prompt 4: Render Setup
The script will show instructions like this:

```
1. Go to: https://dashboard.render.com/create?type=web
2. Connect your GitHub repository: trading-system
3. Configure the service:
   - Name: trading-system-api
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn dashboard_api.app:app --host 0.0.0.0 --port $PORT
   - Instance Type: Free
4. Add Environment Variables:
   - DATABASE_URL = (paste your Neon connection string from Step 3)
```

**Do this now:**
1. Open: https://dashboard.render.com/create?type=web
2. Click **"Connect account"** → **GitHub** → **Authorize**
3. Find repository: `trading-system` → Click **"Connect"**
4. Fill in the form exactly as shown above
5. In **Environment Variables**, add:
   - Key: `DATABASE_URL`
   - Value: (paste from Notepad)
   - Key: `PYTHON_VERSION`
   - Value: `3.11.0`
6. Click **"Create Web Service"**
7. Wait for build (5-10 min) - watch the logs
8. When you see `Application startup complete`, **copy the URL** (like `https://trading-system-api.onrender.com`)
9. Return to PowerShell and press **Enter**

### Prompt 5: Vercel Deployment
The script will deploy your frontend automatically. When asked:

```
? Set up and deploy "~\dashboard_web"? (Y/n)
```
Press **Y** and **Enter**

```
? Which scope do you want to deploy to?
```
Select your account (use arrow keys + Enter)

```
? Link to existing project? (y/N)
```
Press **N** and **Enter**

```
? What's your project's name?
```
Type: `trading-system-dashboard` and **Enter**

```
? In which directory is your code located?
```
Press **Enter** (accepts default `./`)

Vercel will build and deploy (~2 minutes).

**When done, you'll see:**
```
✓ Production: https://trading-system-dashboard.vercel.app
```

**Copy this URL!**

---

## Step 5: Connect Frontend to Backend (2 minutes)

Your frontend needs to know where the backend is:

```powershell
# Still in PowerShell
vercel env add VITE_API_BASE_URL production

# When prompted, paste your Render URL:
# Example: https://trading-system-api.onrender.com
# Press Enter

# Redeploy with new environment variable
cd dashboard_web
vercel --prod
```

---

## Step 6: Test Your Deployment (2 minutes)

1. **Open your frontend:**
   ```powershell
   start https://trading-system-dashboard.vercel.app
   ```

2. **Test symbol search:**
   - Type "AAPL" in the search box
   - You should see Apple stock data load
   - Check the strategy cards show confidence scores

3. **Test watchlist:**
   - Click "Save to Watchlist"
   - Go to Watchlist page (sidebar)
   - You should see AAPL saved

**If everything works:** 🎉 **You're live!**

---

## Your Live URLs

Save these:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | https://trading-system-dashboard.vercel.app | Your main app |
| **Backend API** | https://trading-system-api.onrender.com/docs | API documentation |
| **GitHub Repo** | https://github.com/YOUR_USERNAME/trading-system | Source code |

---

## Auto-Deployment is Enabled!

Every time you push code to GitHub, both frontend and backend auto-deploy:

```powershell
# Make a change
echo "# Test" >> README.md

# Commit and push
git add .
git commit -m "Test auto-deploy"
git push origin main

# Watch deployments happen automatically:
# - Render: https://dashboard.render.com/
# - Vercel: https://vercel.com/dashboard
```

**Deployment time:** ~5-7 minutes (automatic, no manual work)

---

## Optional: Prevent Render From Sleeping

Render free tier sleeps after 15 minutes of inactivity. First load takes ~60 seconds.

**To keep it awake (optional):**

1. Go to: https://uptimerobot.com/
2. Sign up (free)
3. Click **"Add New Monitor"**
4. Configure:
   - Monitor Type: HTTP(s)
   - URL: `https://trading-system-api.onrender.com/health`
   - Monitoring Interval: 5 minutes
5. Click **"Create Monitor"**

Now your API stays awake during active hours.

---

## Troubleshooting

### Frontend shows "Failed to fetch"
**Cause:** Frontend can't reach backend

**Fix:**
```powershell
# Check backend is running
curl https://trading-system-api.onrender.com/health

# If timeout, Render might be sleeping - wait 60s and try again

# Verify environment variable is set
vercel env ls

# If VITE_API_BASE_URL missing, add it:
vercel env add VITE_API_BASE_URL production
# Paste: https://trading-system-api.onrender.com
vercel --prod
```

### Backend shows "Database connection error"
**Cause:** DATABASE_URL not set or incorrect

**Fix:**
1. Go to: https://dashboard.render.com/
2. Click your service
3. Go to: **Environment** tab
4. Verify `DATABASE_URL` is set correctly
5. If wrong, click **Edit** → paste correct value → **Save**
6. Render will redeploy automatically

### GitHub push fails
**Cause:** Authentication issue

**Fix:**
```powershell
# Re-authenticate
gh auth login

# Or use HTTPS with personal access token:
# https://github.com/settings/tokens
```

### Vercel deployment fails
**Cause:** Build error or dependency issue

**Fix:**
```powershell
# View logs
vercel logs

# Force rebuild
vercel --prod --force

# Or check deployment in dashboard:
# https://vercel.com/dashboard → Deployments → [latest] → View Build Logs
```

---

## Need More Help?

- **Detailed guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Full PRD:** [deployment_prd.md](deployment_prd.md)
- **Project docs:** [README.md](README.md)

**Platform Support:**
- Render: https://render.com/docs/support
- Vercel: https://vercel.com/support
- Neon: support@neon.tech

---

## What You've Accomplished

✅ Trading System deployed to production
✅ Frontend on global CDN (Vercel)
✅ Backend API with auto-scaling (Render)
✅ PostgreSQL database (Neon)
✅ Auto-deployment from GitHub
✅ HTTPS/SSL on everything
✅ **$0/month cost**

**Total deployment time:** ~30 minutes
**Maintenance time:** ~0 minutes (auto-updates)

Now you can access your trading system from anywhere, on any device!

---

## Next Steps

**Customize:**
- Add your Alpha Vantage API key for fundamentals
- Set up email alerts (optional)
- Add more symbols to watchlist

**Monitor:**
- Check Render logs: https://dashboard.render.com/
- Check Vercel analytics: https://vercel.com/dashboard
- Check database usage: https://console.neon.tech/

**Share:**
- Send frontend URL to others
- Keep backend URL private (or add authentication later)

**Upgrade (optional):**
- Custom domain ($10-20/year)
- Render Starter plan ($7/mo) to prevent sleeping
- Neon Launch plan ($19/mo) for backups

---

**Congratulations! Your Trading System is live! 🚀**
