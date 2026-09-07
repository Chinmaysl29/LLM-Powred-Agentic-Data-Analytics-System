# Auto-start Docker Desktop and AI Data Analyst OS on Windows boot
param(
    [string]$ProjectDir = "C:\data analyst\ai-data-analyst-os",
    [string]$DockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe",
    [int]$TimeoutSeconds = 180
)

# Setup logging
$LogDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$LogFile = Join-Path $LogDir "startup.log"

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogLine = "[$Timestamp] $Message"
    Write-Output $LogLine
    Add-Content -Path $LogFile -Value $LogLine -Encoding UTF8
}

Write-Log "=========================================================="
Write-Log "Windows Startup Triggered: Launching AI Data Analyst Stack"
Write-Log "=========================================================="

# Step 1: Check if Docker daemon is already responsive
function Test-DockerReady {
    try {
        $null = & docker info 2>&1
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

$isDockerRunning = Test-DockerReady

if (-not $isDockerRunning) {
    Write-Log "Docker daemon is not running. Launching Docker Desktop..."
    if (Test-Path $DockerPath) {
        Start-Process -FilePath $DockerPath
    }
    else {
        Write-Log "WARNING: Docker Desktop executable not found at '$DockerPath'."
    }

    Write-Log "Waiting for Docker daemon to become ready (Timeout: ${TimeoutSeconds}s)..."
    $Elapsed = 0
    $Interval = 3

    while (-not $isDockerRunning -and $Elapsed -lt $TimeoutSeconds) {
        Start-Sleep -Seconds $Interval
        $Elapsed += $Interval
        $isDockerRunning = Test-DockerReady
        if ($Elapsed % 15 -eq 0) {
            Write-Log "Still waiting for Docker daemon... (${Elapsed}s elapsed)"
        }
    }

    if (-not $isDockerRunning) {
        Write-Log "ERROR: Docker daemon did not become ready within $TimeoutSeconds seconds."
        exit 1
    }
    Write-Log "Docker daemon is now ready! (took ~${Elapsed}s)"
}
else {
    Write-Log "Docker daemon is already active and responsive."
}

# Step 2: Run docker compose up -d in project directory
Write-Log "Navigating to project directory: $ProjectDir"
Set-Location -Path $ProjectDir

Write-Log "Executing: docker compose up -d"
try {
    $composeOutput = & docker compose up -d 2>&1
    foreach ($line in $composeOutput) {
        Write-Log "  [docker compose] $line"
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Log "SUCCESS: All AI Data Analyst OS services started successfully!"
    }
    else {
        Write-Log "ERROR: docker compose up -d failed with exit code $LASTEXITCODE"
    }
}
catch {
    Write-Log "ERROR executing docker compose: $_"
}

Write-Log "Startup process completed."
