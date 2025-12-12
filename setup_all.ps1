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
