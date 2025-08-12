#!/bin/bash
# Quick setup script for Unix-like systems

set -e  # Exit on error

echo "Bilbasen Fiat Panda Finder - Unix Setup"
echo "======================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 not found. Please install Python 3.11+ first."
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[INFO] Python $python_version detected"

# Create virtual environment if it doesn't exist  
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "[INFO] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt

# Install Playwright browsers
echo "[INFO] Installing Playwright browsers..."
playwright install

# Create runtime directories
echo "[INFO] Creating runtime directories..."
mkdir -p runtime/{data,fixtures,logs,cache,temp}

# Set up pre-commit hooks if available
if [ -f ".pre-commit-config.yaml" ]; then
    echo "[INFO] Installing pre-commit hooks..."
    pre-commit install || echo "[WARN] Pre-commit setup failed (optional)"
fi

echo ""
echo "======================================"
echo "✅ Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Run: source venv/bin/activate"
echo "2. Run: python launch.py"
echo "3. Visit: http://127.0.0.1:8001"
echo ""