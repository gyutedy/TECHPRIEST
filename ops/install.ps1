param(
  [Parameter(Mandatory = $true)][string]$Project,
  [switch]$Force
)

$source = Split-Path -Parent $PSScriptRoot
$projectPath = (Resolve-Path -LiteralPath $Project).Path
$brainSource = Join-Path $source ".opencode"
$brainTarget = Join-Path $projectPath ".opencode"

New-Item -ItemType Directory -Path $brainTarget -Force | Out-Null

Get-ChildItem -LiteralPath $brainSource -Recurse -File | ForEach-Object {
  $relative = $_.FullName.Substring($brainSource.Length).TrimStart('\', '/')
  $destination = Join-Path $brainTarget $relative
  $parent = Split-Path -Parent $destination
  New-Item -ItemType Directory -Path $parent -Force | Out-Null
  if ((Test-Path -LiteralPath $destination) -and -not $Force) {
    Write-Host "SKIP $relative"
    return
  }
  Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
  Write-Host "COPIED $relative"
}

$ritesTarget = Join-Path $projectPath "RITES.md"
if ((Test-Path -LiteralPath $ritesTarget) -and -not $Force) {
  Write-Host "SKIP RITES.md"
} else {
  Copy-Item -LiteralPath (Join-Path $source "MODELE_RITES.md") -Destination $ritesTarget -Force
  Write-Host "COPIED RITES.md"
}
