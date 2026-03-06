#!/bin/bash
# vm_setup.sh — Run this ONCE on the VM to install pipeline dependencies
# Usage: bash vm_setup.sh
set -e

echo "=== Setting up Scholarship Pipeline on VM ==="

cd ~/scholarship_pipeline 2>/dev/null || {
    echo "ERROR: ~/scholarship_pipeline directory not found."
    echo "Please sync the code first (see README step 1)."
    exit 1
}

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "[1/4] Creating Python venv..."
    python3 -m venv venv
fi

echo "[2/4] Activating venv and installing requirements..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "[3/4] Installing Playwright browsers for Crawl4AI..."
crawl4ai-setup || playwright install chromium

echo "[4/4] Done! Run the pipeline with:"
echo "  source venv/bin/activate"
echo "  python main.py"
