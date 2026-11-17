# Runs code\NN_*.py and code\NN_*.R in numeric order; stops at the first failure.
# The log records step, status and duration only, never script output, so it is safe to share.
# First time, if scripts are blocked:  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "No .venv: py -m venv .venv; .venv\Scripts\pip install -r requirements.txt"; exit 1 }
if (-not (Test-Path "config\config.json")) { Write-Host "config\config.json missing: copy config\config.example.json"; exit 1 }

$log = "output\final_no_phi\logs\run_pipeline.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$commit = "none"
try { $c = git rev-parse --short HEAD 2>$null; if ($c) { $commit = $c } } catch {}
Add-Content $log "run $(Get-Date -Format s) commit $commit"

$scripts = Get-ChildItem code -File | Where-Object { $_.Name -match '^\d{2}_.*\.(py|R)$' } | Sort-Object Name
foreach ($s in $scripts) {
    $step = $s.BaseName
    $sw = [Diagnostics.Stopwatch]::StartNew()
    Write-Host "== $step"
    if ($s.Extension -eq ".py") { & $py $s.FullName } else { & Rscript $s.FullName }
    $status = $LASTEXITCODE
    Add-Content $log "$step exit=$status $([int]$sw.Elapsed.TotalSeconds)s"
    if ($status -ne 0) { Write-Host "FAILED at $step (exit $status). Log: $log"; exit $status }
}
Write-Host "Pipeline complete. Log: $log"
