#!/bin/bash

# SoloTrend X Trading System Setup Script
# This script sets up the development environment for the SoloTrend X Trading System

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create logs and signals directories
echo "Creating log and signal directories..."
mkdir -p logs signals

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env file to configure your Telegram bot token and other settings."
fi

# Make scripts executable
chmod +x run.py
chmod +x tests/generate_test_signal.py

echo "Setup complete!"
echo "Next steps:"
echo "1. Edit the .env file to configure your Telegram bot token and other settings."
echo "2. Run the system with: python run.py"
echo "3. Test signals with: python tests/generate_test_signal.py"