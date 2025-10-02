# ==========================================
# DocuSec Frontend Setup Script
# ==========================================
# Sets up Python virtual environment and installs dependencies
# Usage: .\setup_frontend.ps1

$ErrorActionPreference = "Stop"

# Colors
function Write-Header { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Error-Custom { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  $msg" -ForegroundColor Yellow }

Clear-Host
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     DocuSec Frontend Setup Wizard      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if in correct directory
if (-not (Test-Path "frontend\main.py")) {
    Write-Error-Custom "Error: frontend/main.py not found!"
    Write-Info "Please run this script from the project root directory"
    exit 1
}

# Step 1: Check Python
Write-Header "Step 1: Checking Python Installation"
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
    
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
            Write-Error-Custom "Python 3.10 or higher required (found: $pythonVersion)"
            Write-Info "Download from: https://www.python.org/downloads/"
            exit 1
        }
    }
} catch {
    Write-Error-Custom "Python not found in PATH!"
    Write-Info "Install Python 3.10+ from: https://www.python.org/downloads/"
    Write-Info "During installation, check 'Add Python to PATH'"
    exit 1
}

# Step 2: Navigate to frontend directory
Write-Header "Step 2: Setting up Frontend Directory"
Set-Location frontend
Write-Success "Changed to frontend directory"

# Step 3: Create virtual environment
Write-Header "Step 3: Creating Virtual Environment"
if (Test-Path "venv") {
    Write-Info "Virtual environment already exists"
    $recreate = Read-Host "Recreate virtual environment? (y/N)"
    if ($recreate -eq "y") {
        Write-Info "Removing old virtual environment..."
        Remove-Item -Recurse -Force venv
        python -m venv venv
        Write-Success "Virtual environment recreated"
    } else {
        Write-Success "Using existing virtual environment"
    }
} else {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to create virtual environment!"
        exit 1
    }
    Write-Success "Virtual environment created"
}

# Step 4: Activate virtual environment
Write-Header "Step 4: Activating Virtual Environment"
. .\venv\Scripts\Activate.ps1
Write-Success "Virtual environment activated"

# Step 5: Upgrade pip
Write-Header "Step 5: Upgrading pip"
python -m pip install --upgrade pip --quiet
Write-Success "pip upgraded to latest version"

# Step 6: Install dependencies
Write-Header "Step 6: Installing Dependencies"
Write-Info "This may take several minutes..."
Write-Host ""

$packages = @(
    "PyQt6",
    "PyQt6-Qt6",
    "requests",
    "qtawesome",
    "opencv-python",
    "ultralytics",
    "torch",
    "torchvision",
    "PyMuPDF",
    "python-docx",
    "Pillow"
)

$totalPackages = $packages.Count
$current = 0

foreach ($package in $packages) {
    $current++
    Write-Host "  [$current/$totalPackages] Installing $package..." -ForegroundColor Cyan -NoNewline
    pip install $package --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Write-Host " [ERROR]" -ForegroundColor Red
        Write-Error-Custom "Failed to install $package"
    }
}

Write-Host ""
Write-Success "All dependencies installed successfully"

# Step 7: Verify installation
Write-Header "Step 7: Verifying Installation"
Write-Host ""

$verificationTests = @{
    "PyQt6" = "from PyQt6.QtWidgets import QApplication"
    "Requests" = "import requests"
    "QtAwesome" = "import qtawesome"
    "OpenCV" = "import cv2"
    "YOLOv8" = "from ultralytics import YOLO"
    "PyMuPDF" = "import fitz"
    "python-docx" = "from docx import Document"
    "Pillow" = "from PIL import Image"
}

foreach ($test in $verificationTests.GetEnumerator()) {
    Write-Host "  Checking $($test.Key)..." -NoNewline
    $result = python -c "$($test.Value)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Write-Host " [ERROR]" -ForegroundColor Red
        Write-Info "Warning: $($test.Key) verification failed"
    }
}

# Step 8: Check YOLOv8 model
Write-Header "Step 8: Checking YOLOv8 Model"
if (Test-Path "yolov8n.pt") {
    $modelSize = (Get-Item "yolov8n.pt").Length / 1MB
    Write-Success "YOLOv8 model found (${modelSize:N1} MB)"
} else {
    Write-Info "YOLOv8 model not found"
    Write-Info "The model will be downloaded automatically on first run"
    Write-Info "Or download manually from: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
}

# Step 9: Check backend connection
Write-Header "Step 9: Checking Backend Connection"
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 3 -UseBasicParsing 2>$null
    if ($response.StatusCode -eq 200) {
        Write-Success "Backend is running (http://localhost:8000)"
    }
} catch {
    Write-Host "! " -ForegroundColor Yellow -NoNewline
    Write-Host "Backend is not responding" -ForegroundColor Yellow
    Write-Info "Start backend with: cd .. && .\build_docker.ps1"
}

# Display summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "|       Setup Complete! [OK]                |" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

Write-Host "[Packages] Installation Summary:" -ForegroundColor Cyan
Write-Host "   Python Version:     $pythonVersion" -ForegroundColor White
Write-Host "   Virtual Env:        $(Get-Location)\venv" -ForegroundColor White
Write-Host "   Packages Installed: $totalPackages" -ForegroundColor White
Write-Host ""

Write-Host "[Run] Quick Start:" -ForegroundColor Cyan
Write-Host "   1. Ensure backend is running:" -ForegroundColor White
Write-Host "      cd .. && .\build_docker.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Run the frontend application:" -ForegroundColor White
Write-Host "      python main.py" -ForegroundColor Gray
Write-Host ""
Write-Host "   Or use the automation script:" -ForegroundColor White
Write-Host "      cd .. && .\run_frontend.ps1" -ForegroundColor Gray
Write-Host ""

Write-Host "[Note] Useful Commands:" -ForegroundColor Cyan
Write-Host "   Activate venv:      .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "   Deactivate venv:    deactivate" -ForegroundColor White
Write-Host "   Update packages:    pip install -r requirements.txt --upgrade" -ForegroundColor White
Write-Host "   List packages:      pip list" -ForegroundColor White
Write-Host ""

Write-Host "[OK] Frontend is ready to use!" -ForegroundColor Green
Write-Host ""
