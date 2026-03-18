#!/bin/bash
set -e
echo "Installing frontend dependencies..."
cd "$(dirname "$0")/frontend"
npm install
echo "Starting Kyron Medical UI on http://localhost:5173"
npm run dev
