#!/bin/bash
# Production startup script for SPDCL Automation

set -e

echo "============================================================"
echo "SPDCL Automation - Production Startup"
echo "============================================================"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check environment variables
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    exit 1
fi

if [ ! -f "service-account.json" ]; then
    echo "ERROR: service-account.json not found!"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Run the application
echo "Starting automation..."
python run_complete_system.py

