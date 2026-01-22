# Trading System - Automated Deployment Setup Script
# This script automates the entire deployment process using CLI tools
# Prerequisites: Git, GitHub CLI, Vercel CLI

param(
    [string]$GitHubRepo = "",
    [string]$RenderAppName = "trading-system-api",
    [string]$VercelProjectName = "trading-system-dashboard",
    [switch]$SkipGitHub = $false,
    [switch]$SkipRender = $false,
    [switch]$SkipVercel = $false,
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Trading System Deployment Automation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if command exists
function Test-CommandExists {
    param([string]$Command)
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# ============================================
# STEP 1: Check Prerequisites
# ============================================
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

$missingTools = @()

# Check Git
if (Test-CommandExists "git") {
    try {
        $gitVersion = git --version 2>&1
        Write-Host "  Git installed: $gitVersion" -ForegroundColor Green
    } catch {
        Write-Host "  Git installed" -ForegroundColor Green
    }
} else {
    $missingTools += "Git"
    Write-Host "  Git not installed" -ForegroundColor Red
}

# Check GitHub CLI
if (Test-CommandExists "gh") {
    try {
        $ghVersion = (gh --version 2>&1 | Select-Object -First 1)
        Write-Host "  GitHub CLI installed: $ghVersion" -ForegroundColor Green
    } catch {
        Write-Host "  GitHub CLI installed" -ForegroundColor Green
    }
} else {
    $missingTools += "GitHub CLI (gh)"
    Write-Host "  GitHub CLI not installed" -ForegroundColor Red
}

# Check Vercel CLI
if (Test-CommandExists "vercel") {
    try {
        $vercelVersion = vercel --version 2>&1
        Write-Host "  Vercel CLI installed: $vercelVersion" -ForegroundColor Green
    } catch {
        Write-Host "  Vercel CLI installed" -ForegroundColor Green
    }
} else {
    $missingTools += "Vercel CLI"
    Write-Host "  Vercel CLI not installed" -ForegroundColor Red
}

if ($missingTools.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing required tools: $($missingTools -join ', ')" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install missing tools:" -ForegroundColor Yellow
    if ($missingTools -contains "Git") {
        Write-Host "  Git: winget install Git.Git" -ForegroundColor Cyan
    }
    if ($missingTools -contains "GitHub CLI (gh)") {
        Write-Host "  GitHub CLI: winget install GitHub.cli" -ForegroundColor Cyan
    }
    if ($missingTools -contains "Vercel CLI") {
        Write-Host "  Vercel CLI: npm install -g vercel" -ForegroundColor Cyan
    }
    Write-Host ""
    Write-Host "Or run: .\scripts\install_cli_tools.ps1" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""

# ============================================
# STEP 2: Login to Services
# ============================================
Write-Host "[2/7] Authenticating with services..." -ForegroundColor Yellow

if (-not $SkipGitHub) {
    Write-Host "  Checking GitHub authentication..." -ForegroundColor Cyan
    try {
        $null = gh auth status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Already logged into GitHub CLI" -ForegroundColor Green
        } else {
            Write-Host "  Need to login to GitHub..." -ForegroundColor Yellow
            if (-not $DryRun) {
                gh auth login
            } else {
                Write-Host "  [DRY RUN] Would run: gh auth login" -ForegroundColor Gray
            }
        }
    } catch {
        Write-Host "  Need to login to GitHub..." -ForegroundColor Yellow
        if (-not $DryRun) {
            gh auth login
        } else {
            Write-Host "  [DRY RUN] Would run: gh auth login" -ForegroundColor Gray
        }
    }
}

if (-not $SkipVercel) {
    Write-Host "  Checking Vercel authentication..." -ForegroundColor Cyan
    try {
        $vercelAuth = vercel whoami 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Already logged into Vercel CLI" -ForegroundColor Green
        } else {
            Write-Host "  Need to login to Vercel..." -ForegroundColor Yellow
            if (-not $DryRun) {
                vercel login
            } else {
                Write-Host "  [DRY RUN] Would run: vercel login" -ForegroundColor Gray
            }
        }
    } catch {
        Write-Host "  Need to login to Vercel..." -ForegroundColor Yellow
        if (-not $DryRun) {
            vercel login
        } else {
            Write-Host "  [DRY RUN] Would run: vercel login" -ForegroundColor Gray
        }
    }
}

Write-Host ""

# ============================================
# STEP 3: Create .gitignore
# ============================================
Write-Host "[3/7] Creating .gitignore file..." -ForegroundColor Yellow

$gitignoreContent = @"
# Environment and secrets
.env
.env.local
.env.*.local
config/settings.local.json

# Python
__pycache__/
*.py[cod]
*`$py.class
*.so
.Python
.venv/
trading_env/
venv/
ENV/
env/
*.egg-info/
dist/
build/

# Data and cache (generated at runtime)
data/
*.db
*.sqlite
*.sqlite3

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Frontend
dashboard_web/node_modules/
dashboard_web/dist/
dashboard_web/.next/
dashboard_web/out/
dashboard_web/build/
dashboard_web/.vercel

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
"@

if (-not $DryRun) {
    if (-not (Test-Path ".gitignore")) {
        Set-Content -Path ".gitignore" -Value $gitignoreContent -Encoding UTF8
        Write-Host "  .gitignore created" -ForegroundColor Green
    } else {
        Write-Host "  .gitignore already exists (not overwriting)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [DRY RUN] Would create .gitignore" -ForegroundColor Gray
}

Write-Host ""

# ============================================
# STEP 4: Initialize Git and Create GitHub Repo
# ============================================
if (-not $SkipGitHub) {
    Write-Host "[4/7] Setting up GitHub repository..." -ForegroundColor Yellow

    # Check if already in a git repo
    $isGitRepo = Test-Path ".git"

    if (-not $isGitRepo) {
        Write-Host "  Initializing Git repository..." -ForegroundColor Cyan
        if (-not $DryRun) {
            git init 2>&1 | Out-Null
            Write-Host "  Git repository initialized" -ForegroundColor Green
        } else {
            Write-Host "  [DRY RUN] Would run: git init" -ForegroundColor Gray
        }
    } else {
        Write-Host "  Already a Git repository" -ForegroundColor Green
    }

    # Ask for repository name if not provided
    if ([string]::IsNullOrEmpty($GitHubRepo)) {
        $GitHubRepo = Read-Host "  Enter GitHub repository name (e.g., trading-system)"
        if ([string]::IsNullOrEmpty($GitHubRepo)) {
            $GitHubRepo = "trading-system"
            Write-Host "  Using default: $GitHubRepo" -ForegroundColor Yellow
        }
    }

    # Create GitHub repository
    Write-Host "  Creating GitHub repository: $GitHubRepo" -ForegroundColor Cyan
    if (-not $DryRun) {
        try {
            $createResult = gh repo create $GitHubRepo --private --source=. --remote=origin 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  GitHub repository created: $GitHubRepo" -ForegroundColor Green
            } else {
                Write-Host "  Repository might already exist, checking..." -ForegroundColor Yellow
                try {
                    $username = gh api user -q .login 2>&1
                    $remoteExists = git remote get-url origin 2>&1
                    if ($LASTEXITCODE -ne 0) {
                        git remote add origin "https://github.com/$username/$GitHubRepo.git" 2>&1 | Out-Null
                        Write-Host "  Remote added: origin" -ForegroundColor Green
                    } else {
                        Write-Host "  Remote 'origin' already exists" -ForegroundColor Green
                    }
                } catch {
                    Write-Host "  Warning: Could not configure remote. You may need to add it manually." -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "  Warning: Repository creation had issues: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [DRY RUN] Would run: gh repo create $GitHubRepo --private --source=. --remote=origin" -ForegroundColor Gray
    }

    # Initial commit
    Write-Host "  Creating initial commit..." -ForegroundColor Cyan
    if (-not $DryRun) {
        git add . 2>&1 | Out-Null
        $commitResult = git commit -m "Initial commit - Trading System deployment ready" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Initial commit created" -ForegroundColor Green
        } else {
            Write-Host "  No changes to commit (might be already committed)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [DRY RUN] Would run: git add . && git commit" -ForegroundColor Gray
    }

    # Push to GitHub
    Write-Host "  Pushing to GitHub..." -ForegroundColor Cyan
    if (-not $DryRun) {
        git branch -M main 2>&1 | Out-Null
        $pushResult = git push -u origin main 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Code pushed to GitHub" -ForegroundColor Green
        } else {
            Write-Host "  Push may have failed. Check 'git status' and try manually if needed." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [DRY RUN] Would run: git push -u origin main" -ForegroundColor Gray
    }

    # Get repository URL
    if (-not $DryRun) {
        try {
            $repoUrl = gh repo view --json url -q .url 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Repository URL: $repoUrl" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Repository created (URL not available yet)" -ForegroundColor Yellow
        }
    }

    Write-Host ""
} else {
    Write-Host "[4/7] Skipping GitHub setup" -ForegroundColor Gray
    Write-Host ""
}

# ============================================
# STEP 5: Deploy to Render
# ============================================
if (-not $SkipRender) {
    Write-Host "[5/7] Render Setup Instructions" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Render requires manual setup via web dashboard." -ForegroundColor Yellow
    Write-Host "  Follow these steps:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Open browser: https://dashboard.render.com/create?type=web" -ForegroundColor Cyan
    Write-Host "  2. Click 'Connect account' and select GitHub" -ForegroundColor Cyan
    Write-Host "  3. Find and connect repository: $GitHubRepo" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  4. Configure the service with these settings:" -ForegroundColor Cyan
    Write-Host "     Name: $RenderAppName" -ForegroundColor White
    Write-Host "     Region: Oregon (US West)" -ForegroundColor White
    Write-Host "     Branch: main" -ForegroundColor White
    Write-Host "     Runtime: Python 3" -ForegroundColor White
    Write-Host "     Build Command: pip install -r requirements.txt" -ForegroundColor White
    Write-Host "     Start Command: uvicorn dashboard_api.app:app --host 0.0.0.0 --port `$PORT" -ForegroundColor White
    Write-Host "     Instance Type: Free" -ForegroundColor White
    Write-Host ""
    Write-Host "  5. Add these Environment Variables:" -ForegroundColor Cyan
    Write-Host "     PYTHON_VERSION = 3.11.0" -ForegroundColor White
    Write-Host "     DATABASE_URL = (add after Neon setup)" -ForegroundColor White
    Write-Host ""
    Write-Host "  6. Click 'Create Web Service'" -ForegroundColor Cyan
    Write-Host ""

    if (-not $DryRun) {
        $continue = Read-Host "  Press Enter when Render setup is complete (or Ctrl+C to skip)"
    } else {
        Write-Host "  [DRY RUN] Would pause for user confirmation" -ForegroundColor Gray
    }
    Write-Host ""
} else {
    Write-Host "[5/7] Skipping Render setup" -ForegroundColor Gray
    Write-Host ""
}

# ============================================
# STEP 6: Deploy Frontend to Vercel
# ============================================
if (-not $SkipVercel) {
    Write-Host "[6/7] Deploying frontend to Vercel..." -ForegroundColor Yellow

    # Check if dashboard_web directory exists
    if (-not (Test-Path "dashboard_web")) {
        Write-Host "  Error: dashboard_web directory not found" -ForegroundColor Red
        Write-Host "  Make sure you're in the project root directory" -ForegroundColor Yellow
        Write-Host ""
    } else {
        # Navigate to frontend directory
        Push-Location "dashboard_web"

        Write-Host "  Deploying to Vercel (this may take 2-3 minutes)..." -ForegroundColor Cyan
        if (-not $DryRun) {
            # Deploy with Vercel CLI
            $vercelOutput = vercel --prod 2>&1

            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Frontend deployed to Vercel" -ForegroundColor Green

                # Extract URL from output
                $vercelUrl = $vercelOutput | Select-String -Pattern "https://.*\.vercel\.app" | Select-Object -First 1
                if ($vercelUrl) {
                    Write-Host "  Frontend URL: $vercelUrl" -ForegroundColor Green
                }
            } else {
                Write-Host "  Vercel deployment encountered issues" -ForegroundColor Yellow
                Write-Host "  You can deploy manually later with: cd dashboard_web && vercel --prod" -ForegroundColor Cyan
            }
        } else {
            Write-Host "  [DRY RUN] Would run: vercel --prod" -ForegroundColor Gray
        }

        Pop-Location
        Write-Host ""
    }
} else {
    Write-Host "[6/7] Skipping Vercel setup" -ForegroundColor Gray
    Write-Host ""
}

# ============================================
# STEP 7: Summary and Next Steps
# ============================================
Write-Host "[7/7] Deployment Summary" -ForegroundColor Yellow
Write-Host ""

if (-not $DryRun) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Deployment Configuration Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Create Neon PostgreSQL Database:" -ForegroundColor Cyan
    Write-Host "   - Go to: https://console.neon.tech/app/projects" -ForegroundColor White
    Write-Host "   - Create new project: 'trading-system-db'" -ForegroundColor White
    Write-Host "   - Copy the connection string" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Update Render Environment Variables:" -ForegroundColor Cyan
    Write-Host "   - Go to: https://dashboard.render.com/" -ForegroundColor White
    Write-Host "   - Select your service: $RenderAppName" -ForegroundColor White
    Write-Host "   - Go to Environment tab" -ForegroundColor White
    Write-Host "   - Add: DATABASE_URL = (paste Neon connection string)" -ForegroundColor White
    Write-Host "   - Optional: TS_ALPHA_VANTAGE_KEY = (your API key)" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Update Vercel Environment Variable:" -ForegroundColor Cyan
    Write-Host "   - Go to: https://vercel.com/dashboard" -ForegroundColor White
    Write-Host "   - Select your project" -ForegroundColor White
    Write-Host "   - Go to Settings > Environment Variables" -ForegroundColor White
    Write-Host "   - Add: VITE_API_BASE_URL = https://$RenderAppName.onrender.com" -ForegroundColor White
    Write-Host "   - Redeploy: cd dashboard_web && vercel --prod" -ForegroundColor White
    Write-Host ""
    Write-Host "4. Test Your Deployment:" -ForegroundColor Cyan
    Write-Host "   - Backend API: https://$RenderAppName.onrender.com/docs" -ForegroundColor White
    Write-Host "   - Frontend: (check Vercel dashboard for URL)" -ForegroundColor White
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Auto-Deploy Enabled!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Every 'git push origin main' will trigger automatic deployments." -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host "[DRY RUN] Deployment simulation complete" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Run without -DryRun to execute actual deployment:" -ForegroundColor Yellow
    Write-Host "  .\scripts\deploy_setup.ps1" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  Quick start: QUICKSTART_DEPLOYMENT.md" -ForegroundColor White
Write-Host "  Full guide: DEPLOYMENT_GUIDE.md" -ForegroundColor White
Write-Host "  Technical: deployment_prd.md" -ForegroundColor White
Write-Host ""
