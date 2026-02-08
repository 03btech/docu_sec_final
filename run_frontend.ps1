# ==========================================
# DocuSec Frontend Setup & Run Script
# ==========================================
# Automates virtual environment setup and runs the PyQt6 frontend
# Usage: .\run_frontend.ps1 [-Fresh] [-Update]

param(
    [switch]$Fresh,     # Create fresh virtual environment
    [switch]$Update,    # Update dependencies
    [switch]$Setup      # Setup only, don't run
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Step { param($msg) Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Error-Custom { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  $msg" -ForegroundColor Yellow }

# Banner
Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    DocuSec Frontend Automation         " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "frontend")) {
    Write-Error-Custom "Error: frontend directory not found!"
    Write-Info "Please run this script from the project root directory"
    exit 1
}

# Change to frontend directory
Set-Location frontend

# Check Python installation
Write-Step "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Found: $pythonVersion"
    
    # Check if Python version is 3.10 or higher
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
            Write-Error-Custom "Python 3.10 or higher is required"
            Write-Info "Current version: $pythonVersion"
            exit 1
        }
    }
} catch {
    Write-Error-Custom "Python is not installed or not in PATH!"
    Write-Info "Please install Python 3.10+ from: https://www.python.org/downloads/"
    exit 1
}

# Handle Fresh flag - remove existing venv
if ($Fresh -and (Test-Path "venv")) {
    Write-Step "Removing existing virtual environment..."
    Remove-Item -Recurse -Force venv
    Write-Success "Old virtual environment removed"
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Step "Creating virtual environment..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to create virtual environment!"
        exit 1
    }
    Write-Success "Virtual environment created"
    $Update = $true  # Force update if venv is new
}

# Activate virtual environment
Write-Step "Activating virtual environment..."
$activateScript = "venv\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error-Custom "Virtual environment activation script not found!"
    exit 1
}

# Activate by dot-sourcing
. $activateScript
Write-Success "Virtual environment activated"

# Check if dependencies need to be installed/updated
$requireUpdate = $Update
if (-not $requireUpdate) {
    Write-Step "Checking dependencies..."
    try {
        # Try importing key packages
        $checkImports = python -c "import PyQt6; import requests; import qtawesome; print('OK')" 2>&1
        if ($checkImports -notlike "*OK*") {
            $requireUpdate = $true
            Write-Info "Some dependencies are missing"
        } else {
            Write-Success "All dependencies present"
        }
    } catch {
        $requireUpdate = $true
        Write-Info "Dependencies need to be installed"
    }
}

# Install/update dependencies
if ($requireUpdate) {
    Write-Step "Installing/updating dependencies..."
    Write-Info "This may take a few minutes..."
    
    # Upgrade pip first
    python -m pip install --upgrade pip --quiet
    
    # Install requirements
    pip install -r requirements.txt
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to install dependencies!"
        exit 1
    }
    Write-Success "Dependencies installed successfully"
}

# Check if backend is running
Write-Step "Checking backend connection..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing 2>$null
    if ($response.StatusCode -eq 200) {
        Write-Success "Backend is healthy (http://localhost:8000/health)"
    }
} catch {
    Write-Host "! " -ForegroundColor Yellow -NoNewline
    Write-Host "Backend is not responding!" -ForegroundColor Yellow
    Write-Info "Make sure Docker containers are running: .\build_docker.ps1"
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y") {
        exit 0
    }
}

# Exit if setup-only mode
if ($Setup) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "|         Setup Complete! [OK]              |" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "[Note] Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Ensure backend is running: cd .. && .\build_docker.ps1" -ForegroundColor White
    Write-Host "   2. Run frontend: python main.py" -ForegroundColor White
    Write-Host ""
    exit 0
}

# Run the application
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "|      Starting Frontend Application     |" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

Write-Info "Press Ctrl+C to stop the application"
Write-Host ""

# Run main.py
python main.py

# Check exit code
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Error-Custom "Application exited with error code: $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Success "Application closed normally"
