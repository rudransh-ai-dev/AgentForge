#!/bin/bash

echo "🚀 Starting Ollama model downloads for the AI Agent IDE..."

# List of all models used in the project config
MODELS=(
    "llama3.1:8b"
    "qwen2.5-coder:14b"
    "deepseek-r1:8b"
    "qwen2.5:14b"
    "phi4:latest"
    "gpt-oss:20b"
    "codestral:22b"
    "gemma4:e4b"
)

for model in "${MODELS[@]}"; do
    echo "⬇️ Pulling $model..."
    ollama pull "$model"
done

echo "✅ All models downloaded successfully!"
