#!/bin/bash

# Setup script to download llama.cpp models for LIVA Jetson deployment
# Downloads both thinking and non-thinking models from HuggingFace

set -e

MODELS_DIR="./models"
mkdir -p "$MODELS_DIR"

echo "Downloading llama.cpp models to $MODELS_DIR..."
echo ""

# Model 1: Deepseek R1 Distill (thinking model)
THINKING_MODEL="deepseek-r1-distill-qwen-1.5b-q4_k_m.gguf"
THINKING_REPO="cjpai/deepseek-r1-distill-qwen-1.5b-gguf"
THINKING_PATH="$MODELS_DIR/$THINKING_MODEL"

if [ ! -f "$THINKING_PATH" ]; then
    echo "[1/2] Downloading thinking model (Deepseek R1 Distill 1.5B)..."
    echo "      This is a ~1.2GB file, may take 5-10 minutes on typical internet"
    
    # Try huggingface-cli if available
    if command -v huggingface-cli &> /dev/null; then
        echo "      Using huggingface-cli..."
        huggingface-cli download "$THINKING_REPO" "$THINKING_MODEL" --local-dir "$MODELS_DIR" --local-dir-use-symlinks False
        if [ $? -eq 0 ]; then
            echo "      ✓ Thinking model downloaded"
        else
            echo "      ⚠ huggingface-cli download failed, trying wget..."
            cd "$MODELS_DIR"
            wget --show-progress "https://huggingface.co/$THINKING_REPO/resolve/main/$THINKING_MODEL" -O "$THINKING_MODEL"
            cd - > /dev/null
        fi
    else
        echo "      Using wget..."
        mkdir -p "$MODELS_DIR"
        cd "$MODELS_DIR"
        wget --show-progress "https://huggingface.co/$THINKING_REPO/resolve/main/$THINKING_MODEL" -O "$THINKING_MODEL"
        cd - > /dev/null
        echo "      ✓ Thinking model downloaded"
    fi
else
    echo "[1/2] Thinking model already exists: $THINKING_PATH"
fi

echo ""

# Model 2: Qwen 2.5 Instruct (non-thinking model)
NON_THINKING_MODEL="qwen2.5-1.5b-instruct-q4_k_m.gguf"
NON_THINKING_REPO="cjpai/Qwen2.5-1.5B-Instruct-gguf"
NON_THINKING_PATH="$MODELS_DIR/$NON_THINKING_MODEL"

if [ ! -f "$NON_THINKING_PATH" ]; then
    echo "[2/2] Downloading non-thinking model (Qwen 2.5 Instruct 1.5B)..."
    echo "      This is a ~1.0GB file, may take 5-10 minutes on typical internet"
    
    # Try huggingface-cli if available
    if command -v huggingface-cli &> /dev/null; then
        echo "      Using huggingface-cli..."
        huggingface-cli download "$NON_THINKING_REPO" "$NON_THINKING_MODEL" --local-dir "$MODELS_DIR" --local-dir-use-symlinks False
        if [ $? -eq 0 ]; then
            echo "      ✓ Non-thinking model downloaded"
        else
            echo "      ⚠ huggingface-cli download failed, trying wget..."
            cd "$MODELS_DIR"
            wget --show-progress "https://huggingface.co/$NON_THINKING_REPO/resolve/main/$NON_THINKING_MODEL" -O "$NON_THINKING_MODEL"
            cd - > /dev/null
        fi
    else
        echo "      Using wget..."
        mkdir -p "$MODELS_DIR"
        cd "$MODELS_DIR"
        wget --show-progress "https://huggingface.co/$NON_THINKING_REPO/resolve/main/$NON_THINKING_MODEL" -O "$NON_THINKING_MODEL"
        cd - > /dev/null
        echo "      ✓ Non-thinking model downloaded"
    fi
else
    echo "[2/2] Non-thinking model already exists: $NON_THINKING_PATH"
fi

echo ""
echo "✓ Model setup complete!"
echo ""
echo "Models location:"
ls -lh "$MODELS_DIR"/*.gguf 2>/dev/null || echo "  (No models found - download may have failed)"

echo ""
echo "Next steps:"
echo "  1. Run: docker compose up -d"
echo "  2. Wait ~30 seconds for all services to start"
echo "  3. Check: docker compose logs thinking-llm"
echo "  4. Test: curl http://localhost:5000/health"
