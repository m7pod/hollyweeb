# hollyweeb installer for Windows (PowerShell).
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "== hollyweeb installer ==" -ForegroundColor Magenta

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) {
  Write-Host "Python 3.9+ not found. Install it from https://python.org or the Microsoft Store." -ForegroundColor Red
  exit 1
}

& $py.Source -c "import sys; assert sys.version_info >= (3, 9), 'python 3.9+ required'"

if (Get-Command pipx -ErrorAction SilentlyContinue) {
  Write-Host "installing with pipx (isolated)..." -ForegroundColor Cyan
  pipx install --force $here
} else {
  Write-Host "installing with pip --user..." -ForegroundColor Cyan
  & $py.Source -m pip install --user --upgrade $here
}

Write-Host ""
Write-Host "done. For best results use Windows Terminal (truecolor, emoji, box drawing)." -ForegroundColor Green
Write-Host "run:  hollyweeb" -ForegroundColor Green
