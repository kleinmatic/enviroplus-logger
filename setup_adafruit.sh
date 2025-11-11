#!/bin/bash

# Setup script for Adafruit IO publishing

echo "Setting up Adafruit IO dependencies..."

# Activate virtual environment (adjust path if yours is different)
VENV_PATH="${HOME}/.virtualenvs/pimoroni"
if [ ! -f "${VENV_PATH}/bin/activate" ]; then
    echo "Error: Virtual environment not found at ${VENV_PATH}"
    echo "Please install Pimoroni Enviro+ software first or adjust VENV_PATH"
    exit 1
fi

source "${VENV_PATH}/bin/activate"

# Install required libraries
pip install adafruit-io python-dotenv

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Get your Adafruit IO credentials from https://io.adafruit.com"
echo "2. Click the key icon (🔑) to see your Username and Key"
echo "3. Copy .env.example to .env and add your credentials"
echo "4. Test the script: python3 publish_to_adafruit.py"
echo "5. Set up cron job (see README for instructions)"
