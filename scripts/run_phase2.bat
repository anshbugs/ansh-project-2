@echo off
REM Run Phase 1 (fetch + parse) and Phase 2 (build embeddings) for the Groww MF FAQ RAG chatbot.
REM Ensure .env contains GEMINI_API_KEY=your-key before running.

cd /d "%~dp0.."
echo [Phase 1] Fetching Groww pages...
python -m backend.ingestion.fetch_pages
if errorlevel 1 exit /b 1
echo [Phase 1] Parsing pages and building chunks...
python -m backend.ingestion.parse_pages
if errorlevel 1 exit /b 1
echo [Phase 2] Building embeddings with Gemini...
python -m backend.ingestion.build_embeddings
if errorlevel 1 exit /b 1
echo Done.
