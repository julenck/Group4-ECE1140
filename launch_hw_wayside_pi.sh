#!/bin/bash
# Launch Hardware Wayside on Raspberry Pi
# Usage: ./launch_hw_wayside_pi.sh YOUR_PC_IP

if [ $# -eq 0 ]; then
    echo "❌ ERROR: Please provide your PC's IP address"
    echo "   Usage: ./launch_hw_wayside_pi.sh 192.168.1.100"
    echo "   Find your PC's IP with: ipconfig (on Windows)"
    exit 1
fi

PC_IP="$1"
SERVER_URL="http://$PC_IP:5000"

echo "🌐 Setting SERVER_URL to: $SERVER_URL"
export SERVER_URL="$SERVER_URL"

echo "🔍 Testing environment variable..."
python3 -c "import os; print(f'SERVER_URL: {os.environ.get(\"SERVER_URL\", \"NOT SET\")}')"

echo "🚀 Launching hardware wayside controller..."
python3 combine_ctc_wayside_test.py
