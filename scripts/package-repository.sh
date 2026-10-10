#!/usr/bin/env bash
# Create hcw-networkeyes-addon.zip with repository files at the archive root (no nested parent directory).
# Excludes mirror repository.manifest.json packageExcludes; tests/end_to_end/test_repository_manifest.py checks both.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-hcw-networkeyes-addon.zip}"
rm -f "$OUT"
zip -qr "$OUT" . \
  -x ".git/*" ".venv/*" "*/__pycache__/*" "__pycache__/*" "*.pyc" ".pytest_cache/*" ".ruff_cache/*" ".coverage" "htmlcov/*" \
     "node_modules/*" "*/node_modules/*" "test-results/*" "playwright-report/*" ".env" ".env.*" "*.zip" "*.log" ".local/*" "data/*" ".DS_Store" "$OUT"
# .env.example is excluded by the .env.* pattern above and is part of the repository; add it back.
zip -q "$OUT" .env.example
echo "wrote $OUT ($(du -h "$OUT" | cut -f1)), $(unzip -l "$OUT" | tail -1 | awk '{print $2}') files"
if unzip -l "$OUT" | awk 'NR>3 {print $4}' | grep -E '^(\.git/|\.venv/|node_modules/|.*__pycache__/|\.env$)' >/dev/null; then
  echo "ERROR: excluded path leaked into archive"; exit 1
fi
