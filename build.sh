#!/bin/bash

# Exit on error
set -e

# Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Build completed successfully!" 