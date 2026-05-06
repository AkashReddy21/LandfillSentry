param(
    [string]$ApiHost = "127.0.0.1",
    [int]$ApiPort = 8000,
    [string]$SimSatHost = "127.0.0.1",
    [int]$SimSatPort = 9005,
    [switch]$SkipSmoke,
    [switch]$RestartApi
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot
$logsDir = Join-Path $repoRoot "data/logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$pythonExe = "python"
$venvPython = Join-Path $repoRoot ".venv/Scripts/python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
}

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }
        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) { return }
        $key = $parts[0].Trim()
        $val = $parts[1].Trim()
        if ($val.StartsWith('"') -and $val.EndsWith('"')) {
            $val = $val.Substring(1, $val.Length - 2)
        } elseif ($val.StartsWith("'") -and $val.EndsWith("'")) {
            $val = $val.Substring(1, $val.Length - 2)
        } else {
            $val = ($val -split "\s+#", 2)[0].Trim()
        }
        Set-Item -Path "env:$key" -Value $val
    }
}

function Test-Url {
    param([string]$Url, [int]$TimeoutSec = 8)
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
        return $resp.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Is-Port-Listening {
    param([int]$Port)
    $lines = netstat -ano | Select-String ":$Port"
    if (-not $lines) { return $false }
    foreach ($line in $lines) {
        if ($line.ToString().Contains("LISTENING")) { return $true }
    }
    return $false
}

function Stop-PortListeners {
    param([int]$Port)
    $lines = netstat -ano | Select-String ":$Port" | Select-String "LISTENING"
    if (-not $lines) { return }
    $pids = @()
    foreach ($line in $lines) {
        $raw = ($line.ToString().Trim() -split "\s+")
        if ($raw.Count -gt 0) {
            $pids += $raw[-1]
        }
    }
    $pids = $pids | Sort-Object -Unique
    foreach ($id in $pids) {
        try {
            Stop-Process -Id $id -Force -ErrorAction Stop
            Write-Host "[judge] Stopped listener PID $id on port $Port"
        } catch {
            Write-Host "[judge] Failed to stop PID $id on port ${Port}: $($_.Exception.Message)"
        }
    }
}

Import-DotEnv ".env.local"
if (-not (Test-Path ".env.local")) {
    Import-DotEnv ".env.example"
}

$apiBaseUrl = "http://$ApiHost`:$ApiPort"
$simsatBaseUrl = "http://$SimSatHost`:$SimSatPort"

Write-Host "[judge] repo root: $repoRoot"
Write-Host "[judge] api base: $apiBaseUrl"
Write-Host "[judge] simsat base: $simsatBaseUrl"
Write-Host "[judge] python: $pythonExe"

if ($RestartApi) {
    Write-Host "[judge] RestartApi requested. Stopping existing listeners on port $ApiPort..."
    Stop-PortListeners -Port $ApiPort
    Start-Sleep -Seconds 1
}

$simsatProc = $null
if (-not (Test-Url $simsatBaseUrl 5)) {
    Write-Host "[judge] SimSat is down. Starting local SimSat API..."
    $simsatProc = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList "scripts/run_simsat_api.py","--host","0.0.0.0","--port",$SimSatPort `
        -RedirectStandardOutput (Join-Path $logsDir "simsat.out.log") `
        -RedirectStandardError (Join-Path $logsDir "simsat.err.log") `
        -WindowStyle Hidden `
        -PassThru
    Start-Sleep -Seconds 4
}

if (-not (Test-Url $simsatBaseUrl 8)) {
    Write-Host "[judge] SimSat not ready yet. Waiting up to 90s for cold start..."
    $ready = $false
    for ($i = 0; $i -lt 90; $i++) {
        if (Test-Url $simsatBaseUrl 5) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        throw "[judge] SimSat did not become healthy at $simsatBaseUrl"
    }
}
Write-Host "[judge] SimSat healthy."

$apiProc = $null
if (-not (Is-Port-Listening $ApiPort)) {
    Write-Host "[judge] API is down. Starting uvicorn..."
    $apiProc = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList "-m","uvicorn","apps.api.main:app","--host","0.0.0.0","--port",$ApiPort `
        -RedirectStandardOutput (Join-Path $logsDir "uvicorn.out.log") `
        -RedirectStandardError (Join-Path $logsDir "uvicorn.err.log") `
        -WindowStyle Hidden `
        -PassThru
    Start-Sleep -Seconds 4
}

if (-not (Test-Url "$apiBaseUrl/health" 10)) {
    throw "[judge] API health check failed at $apiBaseUrl/health"
}
if (-not (Test-Url "$apiBaseUrl/ops" 10)) {
    throw "[judge] Frontend route check failed at $apiBaseUrl/ops"
}

Write-Host "[judge] API and frontend are healthy."
if ($apiProc) { Write-Host "[judge] API PID: $($apiProc.Id)" }
if ($simsatProc) { Write-Host "[judge] SimSat PID: $($simsatProc.Id)" }

if (-not $SkipSmoke) {
    Write-Host "[judge] Running live smoke checks..."
    & $pythonExe scripts/live_smoke.py --api-base-url $apiBaseUrl --simsat-base-url $simsatBaseUrl
    if ($LASTEXITCODE -ne 0) {
        throw "[judge] live smoke failed"
    }
}

Write-Host "[judge] READY"
Write-Host "[judge] Open: $apiBaseUrl/ops"
