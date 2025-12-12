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
$envPath = "backend\.env"

if (-not (Test-Path $envPath)) {
    Write-Info ".env file not found. Creating default configuration..."
    
    # Generate random secret key
    $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    
    $envContent = @"
# Database Configuration
DATABASE_URL=postgresql+asyncpg://docusec_user:infosysyrab@db:5432/docu_security_db

# Security
SECRET_KEY=$secretKey

# Application Settings
ENVIRONMENT=production
DEBUG=false

# Database Credentials (for PostgreSQL container)
POSTGRES_DB=docu_security_db
POSTGRES_USER=docusec_user
POSTGRES_PASSWORD=infosysyrab
"@
    
    Set-Content -Path $envPath -Value $envContent
    Write-Success "Created .env file with auto-generated SECRET_KEY"
    Write-Info "Default password: infosysyrab (change in backend\.env)"
}
else {
    Write-Success "Found .env configuration"
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
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 3 -UseBasicParsing 2>$null
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
