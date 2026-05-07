#!/bin/bash

# Master setup script to download all required models (whisper + llama)
# Runs both setup_models.sh and setup_models_llama.sh

set -e

echo "=========================================="
echo "LIVA Jetson AI - Model Setup"
echo "=========================================="
echo ""
echo "This script will download:"
echo "  • Whisper base model (~147 MB)"
echo "  • Qwen 2.5 Instruct model (~1.0 GB)"
echo ""
echo "Total: ~1.15 GB"
echo "Time: 5-10 minutes (depending on internet speed)"
echo ""
echo "Press Enter to continue, or Ctrl+C to cancel..."
read -r

# Run whisper model setup
if [ -f "./setup_models.sh" ]; then
    echo "[1/2] Running whisper model setup..."
    bash ./setup_models.sh
    echo ""
else
    echo "⚠ Warning: setup_models.sh not found, skipping whisper models"
fi

# Run llama model setup
if [ -f "./setup_models_llama.sh" ]; then
    echo "[2/2] Running llama model setup..."
    bash ./setup_models_llama.sh
    echo ""
else
    echo "⚠ Error: setup_models_llama.sh not found"
    exit 1
fi

echo "=========================================="
echo "✓ All models downloaded successfully!"
echo "=========================================="
echo ""
echo "Total models in ./models:"
du -sh ./models
echo ""
ls -lh ./models/*.bin ./models/*.gguf 2>/dev/null || echo "  No model files found"
echo ""
echo "Ready to deploy:"
echo "  docker compose up -d"
