# =============================================================
# AI Data Analyst OS — Auto-Start Script
# =============================================================
# This script is triggered by a Windows Scheduled Task on login.
# It waits for Docker Desktop to become responsive, then starts
# the compose stack in detached mode.
# =============================================================

$ProjectDir = "C:\Users\Likhitha BM\Desktop\LLM powered data analyst"
$LogFile    = "$ProjectDir\infrastructure\startup.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp  $Message" | Out-File -Append -FilePath $LogFile
}

Write-Log "=== Startup script triggered ==="

# ----------------------------------------------------------
# 1. Wait for Docker Desktop to be ready (up to 3 minutes)
# ----------------------------------------------------------
$maxRetries = 36          # 36 x 5s = 180s = 3 minutes
$retryCount = 0

Write-Log "Waiting for Docker Desktop to become ready..."

while ($retryCount -lt $maxRetries) {
    try {
        $output = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker Desktop is ready."
            break
        }
    } catch {
        # docker command not yet available
    }
    $retryCount++
    Write-Log "Docker not ready yet (attempt $retryCount/$maxRetries). Retrying in 5s..."
    Start-Sleep -Seconds 5
}

if ($retryCount -ge $maxRetries) {
    Write-Log "ERROR: Docker Desktop did not become ready within 3 minutes. Aborting."
    exit 1
}

# ----------------------------------------------------------
# 2. Start the compose stack
# ----------------------------------------------------------
Write-Log "Running docker compose up -d in $ProjectDir"

Set-Location $ProjectDir
$result = docker compose up -d 2>&1 | Out-String
Write-Log $result
Write-Log "=== Startup script finished ==="
