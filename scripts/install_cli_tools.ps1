# Install CLI Tools for Deployment
# Run this script first to install all required tools

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Trading System - CLI Tools Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Continue"

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Some installations may require elevated privileges." -ForegroundColor Yellow
    Write-Host "Consider running PowerShell as Administrator." -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        exit
    }
}

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

Write-Host "Checking installed tools..." -ForegroundColor Yellow
Write-Host ""

# ============================================
# 1. Check/Install Git
# ============================================
Write-Host "[1/4] Git" -ForegroundColor Cyan

if (Test-CommandExists "git") {
    try {
        $gitVersion = git --version 2>&1
        Write-Host "  Already installed: $gitVersion" -ForegroundColor Green
    } catch {
        Write-Host "  Already installed" -ForegroundColor Green
    }
} else {
    Write-Host "  Installing Git..." -ForegroundColor Yellow
    try {
        $result = winget install Git.Git --accept-package-agreements --accept-source-agreements 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Git installed successfully" -ForegroundColor Green
            Write-Host "  ! Please restart PowerShell to use Git" -ForegroundColor Yellow
        } else {
            Write-Host "  Failed to install Git" -ForegroundColor Red
            Write-Host "  Please install manually from: https://git-scm.com/download/win" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Failed to install Git: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Please install manually from: https://git-scm.com/download/win" -ForegroundColor Yellow
    }
}
Write-Host ""

# ============================================
# 2. Check/Install GitHub CLI
# ============================================
Write-Host "[2/4] GitHub CLI" -ForegroundColor Cyan

if (Test-CommandExists "gh") {
    try {
        $ghVersion = (gh --version 2>&1 | Select-Object -First 1)
        Write-Host "  Already installed: $ghVersion" -ForegroundColor Green
    } catch {
        Write-Host "  Already installed" -ForegroundColor Green
    }
} else {
    Write-Host "  Installing GitHub CLI..." -ForegroundColor Yellow
    try {
        $result = winget install GitHub.cli --accept-package-agreements --accept-source-agreements 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  GitHub CLI installed successfully" -ForegroundColor Green
            Write-Host "  ! Please restart PowerShell to use GitHub CLI" -ForegroundColor Yellow
        } else {
            Write-Host "  Failed to install GitHub CLI" -ForegroundColor Red
            Write-Host "  Please install manually from: https://cli.github.com/" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Failed to install GitHub CLI: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Please install manually from: https://cli.github.com/" -ForegroundColor Yellow
    }
}
Write-Host ""

# ============================================
# 3. Check/Install Node.js
# ============================================
Write-Host "[3/4] Node.js (required for Vercel CLI)" -ForegroundColor Cyan

if (Test-CommandExists "node") {
    try {
        $nodeVersion = node --version 2>&1
        Write-Host "  Already installed: $nodeVersion" -ForegroundColor Green
    } catch {
        Write-Host "  Already installed" -ForegroundColor Green
    }
} else {
    Write-Host "  Installing Node.js..." -ForegroundColor Yellow
    try {
        $result = winget install OpenJS.NodeJS --accept-package-agreements --accept-source-agreements 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Node.js installed successfully" -ForegroundColor Green
            Write-Host "  ! Please restart PowerShell to use Node.js" -ForegroundColor Yellow

            # Refresh environment variables
            try {
                $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            } catch {
                Write-Host "  ! Could not refresh PATH. Restart PowerShell to use Node.js" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  Failed to install Node.js" -ForegroundColor Red
            Write-Host "  Please install manually from: https://nodejs.org/" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Failed to install Node.js: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Please install manually from: https://nodejs.org/" -ForegroundColor Yellow
    }
}
Write-Host ""

# ============================================
# 4. Check/Install Vercel CLI
# ============================================
Write-Host "[4/4] Vercel CLI" -ForegroundColor Cyan

if (Test-CommandExists "vercel") {
    try {
        $vercelVersion = vercel --version 2>&1
        Write-Host "  Already installed: $vercelVersion" -ForegroundColor Green
    } catch {
        Write-Host "  Already installed" -ForegroundColor Green
    }
} else {
    if (Test-CommandExists "npm") {
        Write-Host "  Installing Vercel CLI via npm..." -ForegroundColor Yellow
        try {
            npm install -g vercel 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Vercel CLI installed successfully" -ForegroundColor Green
            } else {
                Write-Host "  Failed to install Vercel CLI" -ForegroundColor Red
                Write-Host "  Try manually: npm install -g vercel" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  Failed to install Vercel CLI: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "  Try manually: npm install -g vercel" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Cannot install Vercel CLI - Node.js/npm not found" -ForegroundColor Red
        Write-Host "  Please restart PowerShell and run this script again" -ForegroundColor Yellow
    }
}
Write-Host ""

# ============================================
# Optional: PostgreSQL Client
# ============================================
Write-Host "[Optional] PostgreSQL Client (for database testing)" -ForegroundColor Cyan
if (Test-CommandExists "psql") {
    try {
        $psqlVersion = psql --version 2>&1
        Write-Host "  Already installed: $psqlVersion" -ForegroundColor Green
    } catch {
        Write-Host "  Already installed" -ForegroundColor Green
    }
} else {
    Write-Host "  Not installed (optional)" -ForegroundColor Gray
    $installPsql = Read-Host "  Install PostgreSQL client for database testing? (y/N)"
    if ($installPsql -eq 'y' -or $installPsql -eq 'Y') {
        try {
            $result = winget install PostgreSQL.PostgreSQL --accept-package-agreements --accept-source-agreements 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  PostgreSQL installed successfully" -ForegroundColor Green
            } else {
                Write-Host "  Failed to install PostgreSQL" -ForegroundColor Red
            }
        } catch {
            Write-Host "  Failed to install PostgreSQL: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}
Write-Host ""

# ============================================
# Summary
# ============================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$toolsStatus = @(
    @{Name="Git"; Command="git"; Required=$true},
    @{Name="GitHub CLI"; Command="gh"; Required=$true},
    @{Name="Node.js"; Command="node"; Required=$true},
    @{Name="Vercel CLI"; Command="vercel"; Required=$true},
    @{Name="PostgreSQL"; Command="psql"; Required=$false}
)

$allRequired = $true
foreach ($tool in $toolsStatus) {
    $installed = Test-CommandExists $tool.Command

    if ($installed) {
        $status = "[OK]"
        $color = "Green"
    } else {
        $status = "[MISSING]"
        $color = "Red"
    }

    if ($tool.Required) {
        $required = "(Required)"
    } else {
        $required = "(Optional)"
    }

    Write-Host "$status $($tool.Name) $required" -ForegroundColor $color

    if ($tool.Required -and -not $installed) {
        $allRequired = $false
    }
}

Write-Host ""

if ($allRequired) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "All required tools are installed!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Restart PowerShell (to refresh PATH)" -ForegroundColor Cyan
    Write-Host "2. Navigate to project: cd c:\projects\trading_system" -ForegroundColor Cyan
    Write-Host "3. Run deployment: .\scripts\deploy_setup.ps1" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Some required tools are missing!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Restart PowerShell as Administrator" -ForegroundColor Cyan
    Write-Host "2. Run this script again" -ForegroundColor Cyan
    Write-Host "3. If issues persist, install tools manually" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Manual installation links:" -ForegroundColor Yellow
    Write-Host "- Git: https://git-scm.com/download/win" -ForegroundColor Cyan
    Write-Host "- GitHub CLI: https://cli.github.com/" -ForegroundColor Cyan
    Write-Host "- Node.js: https://nodejs.org/" -ForegroundColor Cyan
    Write-Host "- Vercel CLI: npm install -g vercel (after Node.js)" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "Full deployment guide: DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
