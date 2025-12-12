# ==========================================
# DocuSec Docker Management Script
# ==========================================
# Comprehensive management script for Docker operations
# Usage: .\manage_docker.ps1 <command>

param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "backup", "restore", "clean", "shell", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Header { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Error-Custom { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Yellow }

# Banner
function Show-Banner {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "     DocuSec Docker Manager v1.0        " -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

# Help
function Show-Help {
    Show-Banner
    Write-Host "Available Commands:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  start       " -ForegroundColor Green -NoNewline; Write-Host "Start all containers"
    Write-Host "  stop        " -ForegroundColor Green -NoNewline; Write-Host "Stop all containers"
    Write-Host "  restart     " -ForegroundColor Green -NoNewline; Write-Host "Restart all containers"
    Write-Host "  status      " -ForegroundColor Green -NoNewline; Write-Host "Show container status and health"
    Write-Host "  logs        " -ForegroundColor Green -NoNewline; Write-Host "View container logs (live)"
    Write-Host "  backup      " -ForegroundColor Green -NoNewline; Write-Host "Backup database to SQL file"
    Write-Host "  restore     " -ForegroundColor Green -NoNewline; Write-Host "Restore database from backup"
    Write-Host "  clean       " -ForegroundColor Green -NoNewline; Write-Host "Remove containers and volumes"
    Write-Host "  shell       " -ForegroundColor Green -NoNewline; Write-Host "Open shell in backend container"
    Write-Host "  help        " -ForegroundColor Green -NoNewline; Write-Host "Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\manage_docker.ps1 start" -ForegroundColor Gray
    Write-Host "  .\manage_docker.ps1 logs" -ForegroundColor Gray
    Write-Host "  .\manage_docker.ps1 backup" -ForegroundColor Gray
    Write-Host ""
}

# Check Docker
function Test-Docker {
    try {
        docker ps > $null 2>&1
        if ($LASTEXITCODE -ne 0) { return $false }
        return $true
    }
    catch {
        return $false
    }
}

# Main command routing
Show-Banner

if (-not (Test-Docker)) {
    Write-Error-Custom "Docker is not running!"
    Write-Info "Please start Docker Desktop and try again."
    exit 1
}

switch ($Command) {
    "start" {
        Write-Header "Starting Docker Containers"
        docker-compose up -d
        if ($LASTEXITCODE -eq 0) {
            Write-Success "All containers started"
            Start-Sleep -Seconds 3
            docker-compose ps
        }
        else {
            Write-Error-Custom "Failed to start containers"
        }
    }
    
    "stop" {
        Write-Header "Stopping Docker Containers"
        docker-compose stop
        if ($LASTEXITCODE -eq 0) {
            Write-Success "All containers stopped"
        }
        else {
            Write-Error-Custom "Failed to stop containers"
        }
    }
    
    "restart" {
        Write-Header "Restarting Docker Containers"
        docker-compose restart
        if ($LASTEXITCODE -eq 0) {
            Write-Success "All containers restarted"
            Start-Sleep -Seconds 3
            docker-compose ps
        }
        else {
            Write-Error-Custom "Failed to restart containers"
        }
    }
    
    "status" {
        Write-Header "Container Status"
        docker-compose ps
        
        Write-Host ""
        Write-Header "Health Checks"
        
        # Check database
        Write-Host "Database:    " -NoNewline
        $dbHealth = docker inspect --format='{{.State.Health.Status}}' docu_sec_final-db-1 2>$null
        if ($dbHealth -eq "healthy") {
            Write-Host "[OK] Healthy" -ForegroundColor Green
        }
        else {
            Write-Host "[ERROR] $dbHealth" -ForegroundColor Red
        }
        
        # Check backend
        Write-Host "Backend:     " -NoNewline
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 3 -UseBasicParsing 2>$null
            if ($response.StatusCode -eq 200) {
                Write-Host "[OK] Running (http://localhost:8000)" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "[ERROR] Not responding" -ForegroundColor Red
        }
        
        Write-Host ""
        Write-Header "Resource Usage"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        
        Write-Host ""
        Write-Header "Volumes"
        docker volume ls | Select-String "docu_sec"
    }
    
    "logs" {
        Write-Header "Container Logs (Press Ctrl+C to exit)"
        Write-Info "Showing logs for all containers..."
        docker-compose logs -f
    }
    
    "backup" {
        Write-Header "Database Backup"
        
        # Generate timestamp filename
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupFile = "backup_$timestamp.sql"
        
        Write-Info "Creating backup: $backupFile"
        
        # Create backup
        docker exec docu_sec_final-db-1 pg_dump -U docusec_user docu_security_db > $backupFile
        
        if ($LASTEXITCODE -eq 0) {
            $fileSize = (Get-Item $backupFile).Length / 1KB
            Write-Success "Backup created successfully"
            Write-Info "File: $backupFile (${fileSize} KB)"
            Write-Info "Location: $(Get-Location)\$backupFile"
        }
        else {
            Write-Error-Custom "Backup failed"
        }
    }
    
    "restore" {
        Write-Header "Database Restore"
        
        # Find latest backup
        $backups = Get-ChildItem -Filter "backup_*.sql" | Sort-Object LastWriteTime -Descending
        
        if ($backups.Count -eq 0) {
            Write-Error-Custom "No backup files found"
            Write-Info "Backup files should be named: backup_YYYYMMDD_HHMMSS.sql"
            exit 1
        }
        
        Write-Host "Available backups:" -ForegroundColor Yellow
        for ($i = 0; $i -lt [Math]::Min($backups.Count, 5); $i++) {
            Write-Host "  [$($i+1)] $($backups[$i].Name) - $($backups[$i].LastWriteTime)" -ForegroundColor Gray
        }
        
        $choice = Read-Host "`nSelect backup to restore (1-$([Math]::Min($backups.Count, 5))) or Enter to cancel"
        
        if ([string]::IsNullOrWhiteSpace($choice)) {
            Write-Info "Restore cancelled"
            exit 0
        }
        
        $selectedBackup = $backups[$choice - 1]
        
        Write-Warning "This will overwrite the current database!"
        $confirm = Read-Host "Type 'yes' to confirm"
        
        if ($confirm -ne "yes") {
            Write-Info "Restore cancelled"
            exit 0
        }
        
        Write-Info "Restoring from: $($selectedBackup.Name)"
        Get-Content $selectedBackup.FullName | docker exec -i docu_sec_final-db-1 psql -U docusec_user docu_security_db
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Database restored successfully"
        }
        else {
            Write-Error-Custom "Restore failed"
        }
    }
    
    "clean" {
        Write-Header "Clean Docker Resources"
        Write-Warning "This will remove all containers, volumes, and data!"
        $confirm = Read-Host "Type 'DELETE' to confirm"
        
        if ($confirm -ne "DELETE") {
            Write-Info "Clean cancelled"
            exit 0
        }
        
        Write-Info "Stopping containers..."
        docker-compose down -v --remove-orphans
        
        Write-Info "Removing unused resources..."
        docker system prune -f
        
        Write-Success "Cleanup complete"
    }
    
    "shell" {
        Write-Header "Backend Container Shell"
        Write-Info "Opening bash shell in backend container..."
        Write-Info "Type 'exit' to leave the shell"
        Write-Host ""
        docker exec -it docu_sec_final-backend-1 /bin/bash
    }
    
    "help" {
        Show-Help
    }
    
    default {
        Write-Error-Custom "Unknown command: $Command"
        Show-Help
        exit 1
    }
}

Write-Host ""
