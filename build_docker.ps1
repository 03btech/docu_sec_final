# ==========================================
# DocuSec Docker Build Automation Script
# ==========================================
# Quick script to build and start Docker containers
# Usage: .\build_docker.ps1 [-Clean] [-Rebuild] [-Logs]

param(
    [switch]$Clean,      # Remove all containers and volumes before building
    [switch]$Rebuild,    # Force rebuild of images
    [switch]$Logs,       # Show logs after starting
    [switch]$Stop,       # Stop containers
    [switch]$Status      # Show container status
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Step { param($msg) Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Error-Custom { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  $msg" -ForegroundColor Yellow }

# Banner
Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   DocuSec Docker Build Automation     " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if Docker is running
Write-Step "Checking Docker status..."
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker not running" }
    Write-Success "Docker is running"
}
catch {
    Write-Error-Custom "Docker is not running!"
    Write-Info "Please start Docker Desktop and try again."
    exit 1
}

# Handle Stop command
if ($Stop) {
    Write-Step "Stopping all containers..."
    docker-compose down
    Write-Success "All containers stopped"
    exit 0
}

# Handle Status command
if ($Status) {
    Write-Step "Container Status:"
    docker-compose ps
    Write-Host ""
    Write-Step "Docker Images:"
    docker images | Select-String "docu_sec"
    Write-Host ""
    Write-Step "Docker Volumes:"
    docker volume ls | Select-String "docu_sec"
    exit 0
}

# Handle Clean flag
if ($Clean) {
    Write-Step "Cleaning up existing containers and volumes..."
    docker-compose down -v --remove-orphans
    Write-Success "Cleanup complete"
    
    Write-Step "Removing unused Docker resources..."
    docker system prune -f
    Write-Success "Docker cleanup complete"
}

# Check for .env file in backend
Write-Step "Checking environment configuration..."
$envExamplePath = "backend\.env.example"
$envPath = "backend\.env"

# Ensure .env.example exists
if (-not (Test-Path $envExamplePath)) {
    Write-Error-Custom ".env.example not found in backend directory!"
    exit 1
}

# Create .env from template if it doesn't exist
if (-not (Test-Path $envPath)) {
    Write-Info ".env file not found. Creating from template..."

    # Generate cryptographically secure SECRET_KEY
    try {
        $secretKey = python -c "import secrets; print(secrets.token_urlsafe(32))" 2>$null
        if ($LASTEXITCODE -ne 0) { throw "python not found" }
    } catch {
        # Fallback: PowerShell-native cryptographic random generation
        $bytes = New-Object byte[] 32
        $rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
        $rng.GetBytes($bytes)
        $secretKey = [Convert]::ToBase64String($bytes) -replace '[+/=]', ''
        $secretKey = $secretKey.Substring(0, [Math]::Min(32, $secretKey.Length))
        $rng.Dispose()
        Write-Info "Generated SECRET_KEY using PowerShell cryptographic RNG"
    }

    # Read .env.example as template
    $envContent = Get-Content $envExamplePath -Raw

    # Replace only the SECRET_KEY placeholder
    $envContent = $envContent -replace "your-random-32-char-key-here", $secretKey

    # Write to .env
    Set-Content -Path $envPath -Value $envContent -Encoding UTF8
    Write-Success "Created backend\.env from template with auto-generated SECRET_KEY"

    # Validate that placeholder passwords have been changed
    if ($envContent -match "CHANGE_ME_BEFORE_DEPLOY") {
        Write-Host "  [WARNING] backend\.env still contains placeholder passwords!" -ForegroundColor Yellow
        Write-Info "   Edit backend\.env and replace CHANGE_ME_BEFORE_DEPLOY with real passwords:"
        Write-Info "   - POSTGRES_PASSWORD=<your-secure-password>"
        Write-Info "   - DATABASE_URL=postgresql+asyncpg://docusec_user:<your-secure-password>@db:5432/docu_security_db"
    }

    Write-Info "UPDATE backend\.env with your actual Google Cloud Project ID before running:"
    Write-Info "   - GOOGLE_CLOUD_PROJECT_ID=your-actual-project-id"
    Write-Info "   - GOOGLE_CLOUD_REGION=us-central1"
}
else {
    Write-Success "Found backend\.env configuration"

    # Validate required variables are present
    $envContent = Get-Content $envPath -Raw
    $requiredVars = @("GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_CLOUD_REGION", "DATABASE_URL", "SECRET_KEY")

    $missingVars = @()
    foreach ($var in $requiredVars) {
        if ($envContent -notmatch "$var\s*=") {
            $missingVars += $var
        }
    }

    if ($missingVars.Count -gt 0) {
        Write-Host "  [WARNING] Missing variables in backend\.env: $($missingVars -join ', ')" -ForegroundColor Yellow
        Write-Info "Update backend\.env.example and delete backend\.env to regenerate"
    }

    # Reject placeholder passwords in existing .env
    if ($envContent -match "CHANGE_ME_BEFORE_DEPLOY") {
        Write-Error-Custom "backend\.env still contains placeholder passwords (CHANGE_ME_BEFORE_DEPLOY)!"
        Write-Info "Edit backend\.env and set real database passwords before deploying."
        exit 1
    }
}

# Validate credentials folder
$credPath = Join-Path (Split-Path $PSScriptRoot) "credentials\gcp-service-account.json"
if (-not (Test-Path "../credentials/gcp-service-account.json")) {
    Write-Host "  [WARNING] GCP credentials not found!" -ForegroundColor Yellow
    Write-Info "Download your Google service account JSON key and place it in:"
    Write-Info "  c:\Users\bhary\OneDrive\Desktop\docusec_final\credentials\gcp-service-account.json"
    Write-Info "Continuing without credentials (classification will fail at runtime)..."
}
else {
    Write-Success "Found GCP service account credentials"
}

# Build and start containers
if ($Rebuild) {
    Write-Step "Rebuilding Docker images (forced rebuild)..."
    docker-compose build --no-cache
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Docker build failed!"
        exit 1
    }
    Write-Success "Docker images rebuilt successfully"
}

Write-Step "Starting Docker containers..."
if ($Rebuild) {
    docker-compose up -d
}
else {
    docker-compose up -d --build
}

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to start containers!"
    Write-Info "Try running with -Clean flag to remove old containers"
    exit 1
}

Write-Success "Containers started successfully"

# Wait for services to be ready
Write-Step "Waiting for services to initialize..."
Start-Sleep -Seconds 5

# Check database health
Write-Host "  Checking database..." -NoNewline
$dbHealthy = $false
for ($i = 1; $i -le 10; $i++) {
    $dbStatus = docker inspect --format='{{.State.Health.Status}}' docu_sec_final-db-1 2>$null
    if ($dbStatus -eq "healthy") {
        $dbHealthy = $true
        break
    }
    Start-Sleep -Seconds 2
}

if ($dbHealthy) {
    Write-Host " [OK]" -ForegroundColor Green
}
else {
    Write-Host " ... (still starting)" -ForegroundColor Yellow
}

# Check backend health
Write-Host "  Checking backend..." -NoNewline
$backendHealthy = $false
for ($i = 1; $i -le 15; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 3 -UseBasicParsing 2>$null
        if ($response.StatusCode -eq 200) {
            $backendHealthy = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

if ($backendHealthy) {
    Write-Host " [OK]" -ForegroundColor Green
}
else {
    Write-Host " ... (still starting)" -ForegroundColor Yellow
}

# Display status
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "|          Build Complete! [OK]             |" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

Write-Host "[Network] Services:" -ForegroundColor Cyan
Write-Host "   Backend API:     http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs:        http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Database:        localhost:5432" -ForegroundColor White
Write-Host ""

Write-Host "[Status] Container Status:" -ForegroundColor Cyan
docker-compose ps
Write-Host ""

# Get local IP for network access
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.InterfaceAlias -notlike "*Loopback*" -and 
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual"
    } | Select-Object -First 1).IPAddress

if ($localIP) {
    Write-Host "[Link] Network Access:" -ForegroundColor Cyan
    Write-Host "   This PC:         $localIP" -ForegroundColor Yellow
    Write-Host "   API URL:         http://${localIP}:8000" -ForegroundColor Yellow
    Write-Host "   (Update frontend/api/client.py with this URL)" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "[Note] Useful Commands:" -ForegroundColor Cyan
Write-Host "   View logs:       .\build_docker.ps1 -Logs" -ForegroundColor White
Write-Host "   Stop all:        .\build_docker.ps1 -Stop" -ForegroundColor White
Write-Host "   Check status:    .\build_docker.ps1 -Status" -ForegroundColor White
Write-Host "   Clean rebuild:   .\build_docker.ps1 -Clean -Rebuild" -ForegroundColor White
Write-Host "   Backend logs:    docker-compose logs -f backend" -ForegroundColor White
Write-Host "   Database logs:   docker-compose logs -f db" -ForegroundColor White
Write-Host ""

# Show logs if requested
if ($Logs) {
    Write-Step "Showing container logs (Ctrl+C to exit)..."
    docker-compose logs -f
}

Write-Host "[OK] Ready for development!" -ForegroundColor Green
