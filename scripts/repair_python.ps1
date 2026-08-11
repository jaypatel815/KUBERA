# KUBERA local Python repair (ISSUES I005) - user-level only: no admin, no UAC.
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\repair_python.ps1
#
# What it does:
#   1. Picks the newest healthy Python under C:\Program Files\Python3xx
#   2. Rebuilds .venv on it (--clear)
#   3. Reinstalls backend\requirements.txt
#   4. Runs scripts\verify.py - must PASS
#   5. Removes user-PATH entries pointing at Python dirs that no longer exist
#   6. Removes the HKCU py-launcher registration for 3.11 ONLY if its target is gone
# It never touches working installs, system PATH, or anything requiring admin.
# Safe to re-run any time (e.g. after installing a newer Python - it auto-adopts it).

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "== KUBERA Python repair (I005) =="

# --- 1. choose interpreter -------------------------------------------------
$candidates = @(
    "C:\Program Files\Python314\python.exe",
    "C:\Program Files\Python313\python.exe",
    "C:\Program Files\Python312\python.exe",
    "C:\Program Files\Python311\python.exe",
    "C:\Program Files\Python310\python.exe"
)
$python = $null
foreach ($c in $candidates) {
    if (Test-Path $c) { $python = $c; break }
}
if (-not $python) {
    throw "No Python found under C:\Program Files\Python3xx. Install 3.12+ from python.org (check 'Install for all users'), then re-run this script."
}
Write-Host "Using interpreter: $python"
& $python --version

# --- 2. rebuild venv -------------------------------------------------------
$venv = Join-Path $RepoRoot ".venv"
Write-Host "Rebuilding venv at $venv ..."
& $python -m venv $venv --clear
$venvPy = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPy)) { throw "venv creation failed - $venvPy missing" }

# --- 3. dependencies -------------------------------------------------------
Write-Host "Installing dependencies ..."
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r (Join-Path $RepoRoot "backend\requirements.txt") --quiet

# --- 4. verify gate --------------------------------------------------------
Write-Host "Running verify gate ..."
& $venvPy (Join-Path $RepoRoot "scripts\verify.py")
if ($LASTEXITCODE -ne 0) { throw "verify.py FAILED - see output above" }

# --- 5. clean dead user-PATH entries ---------------------------------------
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($null -eq $userPath) { $userPath = "" }
$parts = $userPath -split ";" | Where-Object { $_ -ne "" }
$keep = @()
$removed = @()
foreach ($p in $parts) {
    $isPythonDir = $p -match "\\Programs\\Python\\|\\Python3[0-9]+"
    if ($isPythonDir -and -not (Test-Path $p)) { $removed += $p } else { $keep += $p }
}
if ($removed.Count -gt 0) {
    [Environment]::SetEnvironmentVariable("Path", ($keep -join ";"), "User")
    Write-Host "Removed dead PATH entries:"
    $removed | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "No dead Python PATH entries found."
}

# --- 6. remove orphaned 3.11 launcher registration (guarded) ---------------
$regKey = "HKCU:\Software\Python\PythonCore\3.11"
if (Test-Path $regKey) {
    $installPath = $null
    $ip = Get-ItemProperty -Path (Join-Path $regKey "InstallPath") -ErrorAction SilentlyContinue
    if ($ip) { $installPath = $ip."(default)" }
    $orphaned = $true
    if ($installPath) {
        if (Test-Path (Join-Path $installPath "python.exe")) { $orphaned = $false }
    }
    if ($orphaned) {
        Remove-Item -Path $regKey -Recurse -Force
        Write-Host "Removed orphaned launcher registration: $regKey"
    } else {
        Write-Host "3.11 registration points at a real install - left untouched."
    }
} else {
    Write-Host "No HKCU 3.11 launcher registration - nothing to remove."
}

Write-Host ""
Write-Host "== DONE - venv healthy, verify PASS =="
Write-Host "Next: reload Antigravity (Developer: Reload Window), then select"
Write-Host "      $venvPy"
Write-Host "Tip: 'py -0p' should no longer list the dead 3.11 entry (new shells only)."
