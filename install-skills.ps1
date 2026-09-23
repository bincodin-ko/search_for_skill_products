# Installs this repo's skills into your user-level Claude Code skills folder
# (%USERPROFILE%\.claude\skills), so they work in any folder and in local
# sessions of the Claude desktop app.
#
#   powershell -ExecutionPolicy Bypass -File .\install-skills.ps1
#   powershell -ExecutionPolicy Bypass -File .\install-skills.ps1 -Zip
#
# -Zip also writes dist\<skill>.zip for uploading in the Claude app
# (Customize > Skills > + > Create skill > upload).

param([switch]$Zip)

$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot ".claude\skills"
$dest = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

foreach ($skill in Get-ChildItem $src -Directory) {
    $target = Join-Path $dest $skill.Name
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    # Copy over the top so an existing .venv inside the skill folder survives updates.
    Copy-Item (Join-Path $skill.FullName "*") $target -Recurse -Force
    Write-Host "installed  $($skill.Name)  ->  $target"

    if ($Zip) {
        $dist = Join-Path $PSScriptRoot "dist"
        New-Item -ItemType Directory -Force -Path $dist | Out-Null
        $zipPath = Join-Path $dist "$($skill.Name).zip"
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
        # Zip the folder itself so the archive root is <skill>\SKILL.md.
        Compress-Archive -Path $skill.FullName -DestinationPath $zipPath
        Write-Host "zipped     $($skill.Name)  ->  $zipPath"
    }
}

Write-Host ""
Write-Host "Done. Restart Claude Code (or start a new session) to load the skills."
