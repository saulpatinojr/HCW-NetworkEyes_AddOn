# Create the repository ZIP with repository files at the archive root (no nested parent directory).
# Uses System.IO.Compression directly: Compress-Archive cannot open hidden files (dotfiles may carry the Hidden attribute on
# Windows checkouts). Excludes mirror repository.manifest.json packageExcludes.
param([string]$Out = "hcw-networkeyes-addon.zip")
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$root = (Get-Location).Path
if (Test-Path $Out) { Remove-Item $Out -Force }
$exclude = @('(^|\\|/)\.git(\\|/)', '(^|\\|/)\.venv(\\|/)', '__pycache__', '\.pyc$', '\.pytest_cache(\\|/)', '\.ruff_cache(\\|/)', '(^|\\|/)\.coverage$', '(^|\\|/)htmlcov(\\|/)', 'node_modules', '(^|\\|/)test-results(\\|/)', '(^|\\|/)playwright-report(\\|/)', '(^|\\|/)\.env$', '(^|\\|/)\.env\.(?!example)', '\.zip$', '\.log$', '(^|\\|/)\.local(\\|/)', '(^|\\|/)data(\\|/)', '\.DS_Store$', ([regex]::Escape($Out) + '$'))
$rx = '(' + ($exclude -join ')|(') + ')'
$files = @(Get-ChildItem -Recurse -File -Force | Where-Object { $_.FullName.Substring($root.Length + 1) -notmatch $rx })
if ($files.Count -eq 0) { throw "no files selected for packaging" }
$leaks = @($files | ForEach-Object { $_.FullName.Substring($root.Length + 1).Replace('\', '/') } | Where-Object { $_ -match '^(\.git/|\.venv/|node_modules/|.*__pycache__/|\.env$)' })
if ($leaks.Count -gt 0) { throw "excluded path would leak into the archive: $($leaks -join ', ')" }
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open((Join-Path $root $Out), [System.IO.Compression.ZipArchiveMode]::Create)
try {
  foreach ($f in $files) {
    $rel = $f.FullName.Substring($root.Length + 1).Replace('\', '/')
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, $rel, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
  }
} finally { $zip.Dispose() }
Write-Output "wrote $Out ($([math]::Round((Get-Item $Out).Length / 1MB, 2)) MB, $($files.Count) files)"
