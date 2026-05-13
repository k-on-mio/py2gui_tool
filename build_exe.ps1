$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name py2gui_tool `
  .\py2gui_tool_launcher.py

Write-Host "Build complete: $PSScriptRoot\dist\py2gui_tool.exe"
