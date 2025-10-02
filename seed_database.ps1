# ==========================================
# DocuSec Database Seeding Script
# ==========================================
# Creates initial admin user, test users, and departments
# Usage: .\seed_database.ps1 [-Clean]

param(
    [switch]$Clean  # Remove all existing data before seeding
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Header { param($msg) Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan; Write-Host "║ $msg" -ForegroundColor Cyan; Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Error-Custom { param($msg) Write-Host "✗ $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  $msg" -ForegroundColor Yellow }

Clear-Host
Write-Header "  DocuSec Database Seeding  "

# Check if Docker containers are running
Write-Host "`n▶ Checking Docker containers..." -ForegroundColor Cyan
$dbRunning = docker ps --filter "name=docu_sec-db" --format "{{.Names}}" 2>$null
$backendRunning = docker ps --filter "name=docu_sec-backend" --format "{{.Names}}" 2>$null

if (-not $dbRunning) {
    Write-Error-Custom "Database container is not running!"
    Write-Info "Start containers with: .\build_docker.ps1"
    exit 1
}

if (-not $backendRunning) {
    Write-Error-Custom "Backend container is not running!"
    Write-Info "Start containers with: .\build_docker.ps1"
    exit 1
}

Write-Success "Containers are running"

# Build seed command
$seedCommand = "python seed_data.py"
if ($Clean) {
    $seedCommand += " --clean"
    Write-Host "`n⚠️  WARNING: Clean mode will delete ALL existing data!" -ForegroundColor Yellow
    $confirm = Read-Host "Type 'DELETE' to confirm"
    if ($confirm -ne "DELETE") {
        Write-Info "Seeding cancelled"
        exit 0
    }
}

# Run seed script in backend container
Write-Host "`n▶ Running seed script..." -ForegroundColor Cyan
Write-Host ""

docker exec docu_sec-backend-1 $seedCommand

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Seeding failed!"
    exit 1
}

Write-Host ""
Write-Success "Database seeded successfully!"
Write-Host ""

# Display login information
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║      Default Login Credentials         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "👤 Admin Account:" -ForegroundColor Cyan
Write-Host "   Username: admin" -ForegroundColor White
Write-Host "   Password: Admin@123" -ForegroundColor White
Write-Host "   Email:    admin@docusec.com" -ForegroundColor White
Write-Host ""
Write-Host "👥 Test User Accounts:" -ForegroundColor Cyan
Write-Host "   Username: john.doe, jane.smith, bob.wilson, etc." -ForegroundColor White
Write-Host "   Password: User@123 (for all test users)" -ForegroundColor White
Write-Host ""
Write-Host "📁 Departments Created:" -ForegroundColor Cyan
Write-Host "   IT, Engineering, HR, Finance, Marketing," -ForegroundColor White
Write-Host "   Operations, Legal, Executive" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  Remember to change default passwords in production!" -ForegroundColor Yellow
Write-Host ""
