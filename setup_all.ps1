# ==========================================
# DocuSec Complete Setup Script
# ==========================================
# Sets up both backend (Docker) and frontend (Python)
# Usage: .\setup_all.ps1

$ErrorActionPreference = "Stop"

# Colors
function Write-Step { param($msg) Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Error-Custom { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  $msg" -ForegroundColor Yellow }

# Banner
Clear-Host
Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "        DocuSec Complete Setup Wizard               " -ForegroundColor Cyan
Write-Host "  Automated Backend + Frontend + Database Setup     " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────────
# Pre-flight: GCP Credentials & Environment Config
# ─────────────────────────────────────────────────────
Write-Host "===================================================" -ForegroundColor Yellow
Write-Host "  PRE-FLIGHT: Credentials & Environment Check" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Yellow

# Check GCP credentials
$credDir = Join-Path (Split-Path $PSScriptRoot) "credentials"
$credFile = Join-Path $credDir "gcp-service-account.json"

if (-not (Test-Path $credFile)) {
    Write-Host ""
    Write-Host "  [REQUIRED] GCP Service Account Key not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  DocuSec uses Google Vertex AI for document classification." -ForegroundColor White
    Write-Host "  You need a GCP service account JSON key file." -ForegroundColor White
    Write-Host ""
    Write-Host "  Steps to get one:" -ForegroundColor Cyan
    Write-Host "    1. Go to https://console.cloud.google.com" -ForegroundColor Gray
    Write-Host "    2. Create a project (or use existing)" -ForegroundColor Gray
    Write-Host "    3. Enable the Vertex AI API" -ForegroundColor Gray
    Write-Host "    4. IAM & Admin -> Service Accounts -> Create" -ForegroundColor Gray
    Write-Host "    5. Grant 'Vertex AI User' role" -ForegroundColor Gray
    Write-Host "    6. Create JSON key -> download it" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Expected location:" -ForegroundColor Yellow
    Write-Host "    $credFile" -ForegroundColor White
    Write-Host ""

    # Create credentials directory if needed
    if (-not (Test-Path $credDir)) {
        New-Item -ItemType Directory -Path $credDir -Force | Out-Null
        Write-Info "Created credentials directory: $credDir"
    }

    # Ask user to provide the file
    $keyPath = Read-Host "  Enter path to your gcp-service-account.json (or press Enter to skip)"
    if ($keyPath -and (Test-Path $keyPath)) {
        Copy-Item $keyPath $credFile -Force
        Write-Success "GCP credentials copied to $credFile"
    }
    elseif ($keyPath) {
        Write-Error-Custom "File not found: $keyPath"
        Write-Info "Continuing without credentials — classification will fail at runtime."
        Write-Info "You can place the file later at: $credFile"
    }
    else {
        Write-Info "Skipped — classification will fail until credentials are provided."
        Write-Info "Place the file at: $credFile"
    }
    Write-Host ""
}
else {
    Write-Success "GCP credentials found at $credFile"
}

# Check and configure backend/.env
$envPath = "backend\.env"
$envExamplePath = "backend\.env.example"

if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw

    # Check for placeholder values
    if ($envContent -match "CHANGE_ME_BEFORE_DEPLOY" -or $envContent -match "your-project-id") {
        Write-Host ""
        Write-Host "  [REQUIRED] backend\.env contains placeholder values!" -ForegroundColor Red
        Write-Host ""

        # Prompt for GCP Project ID
        if ($envContent -match "your-project-id") {
            $gcpProject = Read-Host "  Enter your GCP Project ID (e.g., my-project-123456)"
            if ($gcpProject) {
                $envContent = $envContent -replace "your-project-id", $gcpProject
            }
        }

        # Prompt for GCP Region
        if ($envContent -match "GOOGLE_CLOUD_REGION=us-central1") {
            $gcpRegion = Read-Host "  Enter GCP Region (press Enter for us-central1)"
            if ($gcpRegion) {
                $envContent = $envContent -replace "GOOGLE_CLOUD_REGION=us-central1", "GOOGLE_CLOUD_REGION=$gcpRegion"
            }
        }

        # Prompt for database password
        if ($envContent -match "CHANGE_ME_BEFORE_DEPLOY") {
            $dbPass = Read-Host "  Enter a database password (min 8 chars)"
            if ($dbPass -and $dbPass.Length -ge 8) {
                $envContent = $envContent -replace "CHANGE_ME_BEFORE_DEPLOY", $dbPass
                Write-Success "Database password set"
            }
            elseif ($dbPass) {
                Write-Error-Custom "Password too short (min 8 chars). Keeping placeholder — edit backend\.env manually."
            }
            else {
                Write-Error-Custom "No password entered. Edit backend\.env manually before deploy!"
            }
        }

        Set-Content -Path $envPath -Value $envContent -Encoding UTF8
        Write-Success "Updated backend\.env"
        Write-Host ""
    }
    else {
        Write-Success "backend\.env is configured"
    }
}
else {
    Write-Info "backend\.env does not exist yet — build_docker.ps1 will create it from template."
    Write-Info "You will be prompted to configure it after creation."
}

Write-Host ""

# Step 1: Backend Setup
Write-Host "===================================================" -ForegroundColor Yellow
Write-Host "  STEP 1: Backend Setup (Docker)" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Yellow

Write-Step "Building Docker containers..."
& .\build_docker.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Backend setup failed!"
    exit 1
}

Write-Success "Backend setup complete"

# Post-build: Validate .env was populated (build_docker.ps1 may have just created it)
$envPath = "backend\.env"
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    if ($envContent -match "CHANGE_ME_BEFORE_DEPLOY" -or $envContent -match "your-project-id") {
        Write-Host ""
        Write-Host "  [ACTION NEEDED] backend\.env still has placeholder values." -ForegroundColor Yellow
        Write-Host "  The system will start, but classification will fail until configured." -ForegroundColor Yellow
        Write-Host ""

        if ($envContent -match "your-project-id") {
            $gcpProject = Read-Host "  Enter your GCP Project ID (press Enter to skip)"
            if ($gcpProject) {
                $envContent = $envContent -replace "your-project-id", $gcpProject
            }
        }

        if ($envContent -match "CHANGE_ME_BEFORE_DEPLOY") {
            $dbPass = Read-Host "  Enter a database password (press Enter to skip)"
            if ($dbPass -and $dbPass.Length -ge 8) {
                $envContent = $envContent -replace "CHANGE_ME_BEFORE_DEPLOY", $dbPass
            }
        }

        Set-Content -Path $envPath -Value $envContent -Encoding UTF8

        # Restart containers if we changed the env
        if ($gcpProject -or ($dbPass -and $dbPass.Length -ge 8)) {
            Write-Info "Restarting containers with updated configuration..."
            docker-compose down 2>$null
            docker-compose up -d --build
        }
    }
}

# Wait for backend to be fully ready
Write-Step "Waiting for backend to be ready..."
Start-Sleep -Seconds 5

# Step 2: Database Seeding
Write-Host ""
Write-Host "===================================================" -ForegroundColor Yellow
Write-Host "  STEP 2: Database Seeding" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Yellow

Write-Step "Seeding database with initial data..."
& .\seed_database.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Database seeding failed!"
    exit 1
}

Write-Success "Database seeding complete"

# Step 3: Frontend Setup
Write-Host ""
Write-Host "===================================================" -ForegroundColor Yellow
Write-Host "  STEP 3: Frontend Setup (Python)" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Yellow

Write-Step "Setting up frontend environment..."
& .\setup_frontend.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Frontend setup failed!"
    exit 1
}

Write-Success "Frontend setup complete"

# Final Summary
Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "|           Setup Complete!                      |" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""

Write-Host " What's Been Set Up:" -ForegroundColor Cyan
Write-Host "   1. [OK] Docker containers (Backend + Database)" -ForegroundColor Green
Write-Host "   2. [OK] Database seeded with admin and test users" -ForegroundColor Green
Write-Host "   3. [OK] Frontend Python environment and dependencies" -ForegroundColor Green
Write-Host ""

Write-Host "[Network] Services Running:" -ForegroundColor Cyan
Write-Host "   Backend API:     http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs:        http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Database:        localhost:5432" -ForegroundColor White
Write-Host ""

Write-Host "[Security] Default Login Credentials:" -ForegroundColor Cyan
Write-Host "   Admin Username:  admin" -ForegroundColor White
Write-Host "   Admin Password:  Admin@123" -ForegroundColor White
Write-Host ""
Write-Host "   User Username:   john.doe (or jane.smith, bob.wilson, etc.)" -ForegroundColor White
Write-Host "   User Password:   User@123" -ForegroundColor White
Write-Host ""

Write-Host "[Run] Run Frontend Application:" -ForegroundColor Cyan
Write-Host "   Option 1 (Quick):    .\run_frontend.ps1" -ForegroundColor White
Write-Host "   Option 2 (Manual):   cd frontend && python main.py" -ForegroundColor White
Write-Host ""

Write-Host "[Note] Useful Management Commands:" -ForegroundColor Cyan
Write-Host "   View backend logs:   .\manage_docker.ps1 logs" -ForegroundColor White
Write-Host "   Stop backend:        .\manage_docker.ps1 stop" -ForegroundColor White
Write-Host "   Restart backend:     .\manage_docker.ps1 restart" -ForegroundColor White
Write-Host "   Backup database:     .\manage_docker.ps1 backup" -ForegroundColor White
Write-Host "   Run frontend:        .\run_frontend.ps1" -ForegroundColor White
Write-Host ""

Write-Host "[Tip] Pro Tips:" -ForegroundColor Cyan
Write-Host "   • Keep Docker Desktop running while using the app" -ForegroundColor Gray
Write-Host "   • Check backend health: .\manage_docker.ps1 status" -ForegroundColor Gray
Write-Host "   • Change default passwords in production!" -ForegroundColor Gray
Write-Host "   • Read README.md for detailed documentation" -ForegroundColor Gray
Write-Host ""

Write-Host "[OK] Ready to use DocuSec! Run frontend now? (Y/n): " -NoNewline -ForegroundColor Green
$runNow = Read-Host

if ($runNow -eq "" -or $runNow -eq "y" -or $runNow -eq "Y") {
    Write-Host ""
    Write-Step "Launching frontend application..."
    # Make sure we're in the project root directory
    Set-Location $PSScriptRoot
    & "$PSScriptRoot\run_frontend.ps1"
}
else {
    Write-Host ""
    Write-Info "Run frontend later with: .\run_frontend.ps1"
    Write-Host ""
}
