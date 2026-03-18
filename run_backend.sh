#!/bin/bash
set -e
echo "Installing backend dependencies..."
cd "$(dirname "$0")/backend"
pip install -r requirements.txt -q
echo "Starting Kyron Medical API on http://localhost:8000"
uvicorn main:app --reload --port 8000
