# DocuSec Backend Server Setup Script
# This script sets up the complete backend with PostgreSQL in Docker
# Run this on a separate Windows PC to deploy the backend server

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "DocuSec Backend Server Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if a command exists
function Test-Command {
    param($Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# Step 1: Check prerequisites
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

if (-not (Test-Command docker)) {
    Write-Host "ERROR: Docker is not installed!" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Red
    exit 1
}

if (-not (Test-Command docker-compose)) {
    Write-Host "ERROR: Docker Compose is not installed!" -ForegroundColor Red
    Write-Host "Docker Compose usually comes with Docker Desktop. Please reinstall Docker." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Docker is installed" -ForegroundColor Green
Write-Host "[OK] Docker Compose is installed" -ForegroundColor Green

# Step 2: Check if Docker is running
Write-Host ""
Write-Host "[2/7] Checking if Docker is running..." -ForegroundColor Yellow

docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Docker is running" -ForegroundColor Green

# Step 3: Create .env file if it doesn't exist
Write-Host ""
Write-Host "[3/7] Setting up environment configuration..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Cyan
    
    # Generate a random secret key
    $SecretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    
    $envContent = @"
# Database Configuration
DATABASE_URL=postgresql+asyncpg://docusec_user:infosysyrab@db:5432/docu_security_db

# Security
SECRET_KEY=$SecretKey

# Application Settings
ENVIRONMENT=production
DEBUG=false

# Database Credentials (for PostgreSQL container)
POSTGRES_DB=docu_security_db
POSTGRES_USER=docusec_user
POSTGRES_PASSWORD=infosysyrab
"@
    
    Set-Content -Path ".env" -Value $envContent
    Write-Host "[OK] Created .env file with auto-generated SECRET_KEY" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Please review .env file and update passwords if needed!" -ForegroundColor Yellow
    Write-Host "Default password: infosysyrab" -ForegroundColor Yellow
} else {
    Write-Host "[OK] .env file already exists" -ForegroundColor Green
}

# Step 4: Create docker-compose.yml for backend server
Write-Host ""
Write-Host "[4/7] Creating Docker Compose configuration..." -ForegroundColor Yellow

$dockerComposeContent = @"
version: '3.8'

services:
  db:
    image: postgres:13-alpine
    container_name: docusec-postgres
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: `${POSTGRES_DB}
      POSTGRES_USER: `${POSTGRES_USER}
      POSTGRES_PASSWORD: `${POSTGRES_PASSWORD}
      TZ: UTC
      PGTZ: UTC
    env_file:
      - .env
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U `${POSTGRES_USER} -d `${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - docusec-network

  backend:
    build: .
    container_name: docusec-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - uploaded_files_data:/app/uploaded_files
      - ./ml:/app/ml
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    networks:
      - docusec-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
    driver: local
  uploaded_files_data:
    driver: local

networks:
  docusec-network:
    driver: bridge
"@

Set-Content -Path "docker-compose.backend.yml" -Value $dockerComposeContent
Write-Host "[OK] Created docker-compose.backend.yml" -ForegroundColor Green

# Step 5: Stop and remove existing containers (if any)
Write-Host ""
Write-Host "[5/7] Cleaning up existing containers..." -ForegroundColor Yellow

docker-compose -f docker-compose.backend.yml down -v 2>$null
Write-Host "[OK] Cleaned up existing containers" -ForegroundColor Green

# Step 6: Build and start containers
Write-Host ""
Write-Host "[6/7] Building and starting Docker containers..." -ForegroundColor Yellow
Write-Host "This may take several minutes on first run..." -ForegroundColor Cyan

docker-compose -f docker-compose.backend.yml up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start containers!" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Containers started successfully" -ForegroundColor Green

# Step 7: Wait for services to be healthy and show status
Write-Host ""
Write-Host "[7/7] Waiting for services to be ready..." -ForegroundColor Yellow

Start-Sleep -Seconds 10

$maxAttempts = 30
$attempt = 0
$backendHealthy = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Host "Checking backend health (attempt $attempt/$maxAttempts)..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $backendHealthy = $true
            break
        }
    } catch {
        # Service not ready yet
    }
    
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

if ($backendHealthy) {
    Write-Host "[OK] Backend API is running at: http://localhost:8000" -ForegroundColor Green
    Write-Host "[OK] API Documentation: http://localhost:8000/docs" -ForegroundColor Green
    Write-Host "[OK] Database is running on port 5432" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Backend is starting but not yet responding" -ForegroundColor Yellow
    Write-Host "  Please wait a few more seconds and check: http://localhost:8000" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Container Status:" -ForegroundColor Cyan
docker-compose -f docker-compose.backend.yml ps

Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "  View logs:           docker-compose -f docker-compose.backend.yml logs -f" -ForegroundColor White
Write-Host "  Stop services:       docker-compose -f docker-compose.backend.yml stop" -ForegroundColor White
Write-Host "  Start services:      docker-compose -f docker-compose.backend.yml start" -ForegroundColor White
Write-Host "  Restart services:    docker-compose -f docker-compose.backend.yml restart" -ForegroundColor White
Write-Host "  Remove everything:   docker-compose -f docker-compose.backend.yml down -v" -ForegroundColor White
Write-Host ""

Write-Host "Network Access:" -ForegroundColor Cyan
Write-Host "  To access from other computers on your network:" -ForegroundColor White
Write-Host "  1. Find this PC's IP address: ipconfig" -ForegroundColor White
Write-Host "  2. Configure firewall to allow port 8000" -ForegroundColor White
Write-Host "  3. Update frontend to use: http://<THIS-PC-IP>:8000" -ForegroundColor White
Write-Host ""

# Get local IP address
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1).IPAddress

if ($localIP) {
    Write-Host "  This PC's IP address: $localIP" -ForegroundColor Yellow
    Write-Host "  Frontend should connect to: http://${localIP}:8000" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
