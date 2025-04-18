#!/bin/bash

# Exit on error
set -e

# Set Python version
export PYTHON_VERSION=3.11.7

echo "Setting up Python ${PYTHON_VERSION}..."
pyenv install ${PYTHON_VERSION} -s || true
pyenv global ${PYTHON_VERSION}

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating necessary directories..."
mkdir -p logs
mkdir -p static/uploads

echo "Setting up environment..."
if [ ! -f .env ]; then
    if [ "$ENVIRONMENT" = "production" ]; then
        cp .env.production .env
    else
        cp .env.example .env
    fi
fi

echo "Running database migrations..."
python scripts/init_db.py

echo "Running tests..."
if [ "$SKIP_TESTS" != "true" ]; then
    python -m pytest tests/ -v
fi

echo "Build completed successfully!" 