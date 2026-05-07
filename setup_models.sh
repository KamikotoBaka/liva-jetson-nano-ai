#!/usr/bin/env bash

set -euo pipefail

MODEL_NAME="${1:-base}"
MODEL_DIR="${2:-$(pwd)/models}"
MODEL_FILE="${MODEL_DIR}/ggml-${MODEL_NAME}.bin"

mkdir -p "${MODEL_DIR}"

if [ -f "${MODEL_FILE}" ]; then
	echo "Model already exists: ${MODEL_FILE}"
	exit 0
fi

echo "Downloading whisper model: ${MODEL_NAME}"
echo "Target: ${MODEL_FILE}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git "${TMP_DIR}/whisper.cpp"
cd "${TMP_DIR}/whisper.cpp"

./models/download-ggml-model.sh "${MODEL_NAME}" "${MODEL_DIR}"

echo "Done: ${MODEL_FILE}"
