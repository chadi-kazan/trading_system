# Deployment Scripts

This folder contains automated scripts for deploying the Trading System to free hosting platforms.

---

## Quick Start

```powershell
# 1. Install CLI tools (run as Administrator)
.\install_cli_tools.ps1

# 2. Restart PowerShell

# 3. Deploy everything
.\deploy_setup.ps1
```

---

## Scripts Overview

### install_cli_tools.ps1
**Purpose:** Install required CLI tools for deployment

**What it installs:**
- Git
- GitHub CLI (gh)
- Node.js
- Vercel CLI
- PostgreSQL client (optional)

**Usage:**
```powershell
# Run as Administrator
.\install_cli_tools.ps1
```

**Requirements:**
- Windows 10/11
- PowerShell 5.1+
- Administrator privileges (recommended)
- Internet connection

**Output:**
- ✓ Tools installed via winget
- ✓ Verification of each tool
- ✓ Summary of installation status

---

### deploy_setup.ps1
**Purpose:** Automated deployment to GitHub, Render, and Vercel

**What it does:**
1. Checks prerequisites (Git, GitHub CLI, Vercel CLI)
2. Logs into GitHub and Vercel
3. Creates .gitignore file
4. Initializes Git repository
5. Creates GitHub repository
6. Pushes code to GitHub
7. Shows Render setup instructions
8. Deploys frontend to Vercel
9. Enables auto-deployment

**Usage:**
```powershell
# Dry run (see what will happen without doing it)
.\deploy_setup.ps1 -DryRun

# Actual deployment
.\deploy_setup.ps1

# Custom repository name
.\deploy_setup.ps1 -GitHubRepo "my-trading-system"

# Skip certain steps
.\deploy_setup.ps1 -SkipGitHub
.\deploy_setup.ps1 -SkipVercel
```

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `-GitHubRepo` | String | GitHub repository name | (prompts user) |
| `-RenderAppName` | String | Render service name | trading-system-api |
| `-VercelProjectName` | String | Vercel project name | trading-system-dashboard |
| `-SkipGitHub` | Switch | Skip GitHub setup | false |
| `-SkipRender` | Switch | Skip Render instructions | false |
| `-SkipVercel` | Switch | Skip Vercel deployment | false |
| `-DryRun` | Switch | Simulate without executing | false |

**Examples:**

```powershell
# Deploy everything with defaults
.\deploy_setup.ps1

# Deploy only to Vercel (skip GitHub)
.\deploy_setup.ps1 -SkipGitHub

# Use custom names
.\deploy_setup.ps1 -GitHubRepo "stock-analyzer" -RenderAppName "stock-api"

# Test without actually deploying
.\deploy_setup.ps1 -DryRun
```

**Requirements:**
- Git installed and configured
- GitHub CLI installed and authenticated
- Vercel CLI installed and authenticated
- GitHub, Render, Vercel, and Neon accounts created

**Interactive Prompts:**
The script will pause and ask for:
1. GitHub repository name (if not provided)
2. GitHub authentication (browser opens)
3. Vercel authentication (browser opens)
4. Render manual setup confirmation

**Expected Output:**
```
========================================
Trading System Deployment Automation
========================================

[1/7] Checking prerequisites...
✓ Git installed: git version 2.x.x
✓ GitHub CLI installed: gh version 2.x.x
✓ Vercel CLI installed: 33.x.x

[2/7] Authenticating with services...
✓ Already logged into GitHub CLI
✓ Already logged into Vercel CLI: username

[3/7] Creating .gitignore file...
✓ .gitignore created

[4/7] Setting up GitHub repository...
✓ Git repository initialized
✓ GitHub repository created: trading-system
✓ Initial commit created
✓ Code pushed to GitHub
✓ Repository URL: https://github.com/username/trading-system

[5/7] Deploying to Render...
NOTE: Render CLI has limited functionality.
Please complete the following steps manually:
1. Go to: https://dashboard.render.com/create?type=web
2. Connect your GitHub repository: trading-system
...
Press Enter when Render setup is complete...

[6/7] Deploying frontend to Vercel...
✓ Frontend deployed to Vercel
✓ Frontend URL: https://trading-system-dashboard.vercel.app

[7/7] Deployment Summary
========================================
Deployment Configuration Complete!
========================================

Auto-Deploy is now enabled!
Every git push to main will trigger automatic deployments.
```

---

## Troubleshooting

### Script won't run
```
cannot be loaded because running scripts is disabled on this system
```

**Fix:**
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Git not found after installation
**Fix:** Restart PowerShell

### GitHub CLI authentication fails
**Fix:**
```powershell
gh auth logout
gh auth login
```

### Vercel deployment fails
**Fix:**
```powershell
# Force redeploy
cd dashboard_web
vercel --prod --force
```

### Missing tools not installing
**Fix:** Run PowerShell as Administrator

---

## Manual Deployment (Alternative)

If scripts don't work, follow the manual guide:
- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)

---

## After Running Scripts

### Next Steps:

1. **Create Neon Database:**
   - Go to: https://console.neon.tech/app/projects
   - Create new project: "trading-system-db"
   - Copy connection string

2. **Update Render Environment Variables:**
   - Go to your Render service
   - Add: `DATABASE_URL` = (Neon connection string)

3. **Update Vercel Environment Variable:**
   - Go to Vercel project settings
   - Add: `VITE_API_BASE_URL` = (Render app URL)
   - Redeploy: `vercel --prod`

4. **Test Deployment:**
   - Frontend: https://your-project.vercel.app
   - Backend: https://your-app.onrender.com/docs

### Auto-Deployment

Both Render and Vercel watch your GitHub repository.

**To deploy updates:**
```powershell
git add .
git commit -m "Update feature"
git push origin main

# Automatic triggers:
# - Vercel starts building (~2 min)
# - Render starts building (~5 min)
# - Both deploy automatically on success
```

---

## Additional Resources

- **Quick Start:** [QUICKSTART_DEPLOYMENT.md](../QUICKSTART_DEPLOYMENT.md)
- **Detailed Guide:** [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)
- **PRD:** [deployment_prd.md](../deployment_prd.md)
- **Summary:** [DEPLOYMENT_FILES_SUMMARY.md](../DEPLOYMENT_FILES_SUMMARY.md)

---

## Support

- **Render:** https://render.com/docs/support
- **Vercel:** https://vercel.com/support
- **GitHub CLI:** https://cli.github.com/manual/

---

**Ready to deploy?**

```powershell
.\install_cli_tools.ps1
# Restart PowerShell
.\deploy_setup.ps1
```
