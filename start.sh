#!/bin/bash
echo "========================================"
echo "  Ad Vault — Meta Ad Archiver"
echo "========================================"

# Check python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install from https://python.org"
    exit 1
fi

# Check/install deps
echo "Checking dependencies..."
python3 -c "import flask" 2>/dev/null || pip install flask --quiet
python3 -c "import playwright" 2>/dev/null || pip install playwright --quiet
python3 -c "from playwright.sync_api import sync_playwright" 2>/dev/null || playwright install chromium --quiet

echo "Starting server..."
echo "Opening http://localhost:5000 in browser..."

# Open browser after short delay
(sleep 2 && open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null) &

# Run app
cd "$(dirname "$0")"
python3 app.py
