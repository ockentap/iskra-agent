# Iskra — Windows bootstrap.
# Clones the fork and runs the repo setup so a fresh Windows machine lands a
# working `iskra` CLI. For the smoothest experience use WSL2 and install.sh;
# this native path needs git and PowerShell 5.1+.
#   iex (irm https://ockentap.github.io/iskra-agent/install.ps1)
$ErrorActionPreference = 'Stop'

$repo = if ($env:HERMES_REPO_URL) { $env:HERMES_REPO_URL } else { 'https://github.com/ockentap/iskra-agent.git' }
$iskraHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $HOME '.iskra' }
$dir = Join-Path $iskraHome 'iskra-agent'

Write-Host ''
Write-Host 'Iskra — the self-improving AI agent' -ForegroundColor Yellow
Write-Host ''

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw 'git is required. Install Git for Windows (https://git-scm.com/download/win) and re-run.'
}

if (-not (Test-Path (Join-Path $dir '.git'))) {
  Write-Host "Cloning $repo -> $dir"
  git clone $repo $dir
  if ($LASTEXITCODE -ne 0) { throw 'git clone failed.' }
} else {
  Write-Host "Updating existing checkout at $dir"
  git -C $dir pull --ff-only
}

Set-Location $dir
# The repo setup provisions the pinned Python/toolchain and publishes the CLI.
& (Join-Path $dir 'setup-hermes.ps1')

Write-Host ''
Write-Host 'Iskra is installed. Activate the environment, then start:' -ForegroundColor Green
Write-Host '  .\activate.ps1'
Write-Host '  iskra setup'
Write-Host ''