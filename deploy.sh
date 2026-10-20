#!/usr/bin/env bash
set -e

echo "=== Telegram OCR Bot Deployment Script ==="

# 1. Install system fonts and python
echo "Installing system packages & fonts..."
apt-get update
apt-get install -y python3 python3-venv python3-pip fonts-dejavu-core fonts-liberation

# 2. Setup virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. Create .env if not exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env from .env.example. Please edit it with your keys!"
    fi
fi

echo "=== Setup Complete! ==="
echo "To start the bot in background: nohup ./venv/bin/python main.py > bot.log 2>&1 &"
echo "Or using Docker: docker compose up -d --build"
