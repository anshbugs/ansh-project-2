# Run Phase 1 (fetch + parse) and Phase 2 (build embeddings).
# Ensure .env contains GEMINI_API_KEY=your-key before running.
Set-Location "$PSScriptRoot\.."

Write-Host "[Phase 1] Fetching Groww pages..."
python -m backend.ingestion.fetch_pages
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[Phase 1] Parsing pages and building chunks..."
python -m backend.ingestion.parse_pages
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[Phase 2] Building embeddings with Gemini..."
python -m backend.ingestion.build_embeddings
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done."
