#!/bin/bash
# Setup script for uv, virtual environment, and dependencies

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
fi

# Create virtual environment
echo "Creating virtual environment..."
uv venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install -e .

# Install development dependencies
echo "Installing development dependencies..."
uv pip install -r requirements-dev.txt

echo "Setup complete! Activate the virtual environment with:"
echo "source .venv/bin/activate" 