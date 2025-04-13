#!/bin/bash

# Exit on error
set -e

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating necessary directories..."
mkdir -p logs
mkdir -p static/uploads

echo "Setting up environment..."
if [ ! -f .env ]; then
    cp .env.production .env
fi

echo "Running database migrations..."
python scripts/init_db.py

echo "Build completed successfully!" 