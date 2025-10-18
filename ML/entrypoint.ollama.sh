#!/bin/sh
set -e

model_url="https://huggingface.co/ilyagusev/saiga_mistral_7b_gguf/resolve/main/model-q4_K.gguf"
model_dir="/root/.ollama/models"
model_filename="model-q4_k.gguf"
model_path="$model_dir/$model_filename"
expected_sha256="2798f33ff63c791a21f05c1ee9a10bc95630b17225c140c197188a3d5cf32644"

echo "ollama entrypoint: checking for language model..."
mkdir -p "$model_dir"

if [ -f "$model_path" ]; then
    echo "ollama entrypoint: model file found. verifying hash..."
    current_sha256=$(sha256sum "$model_path" | awk '{print $1}')
    if [ "$current_sha256" = "$expected_sha256" ]; then
        echo "ollama entrypoint: sha256 hash matches. skipping download."
    else
        echo "ollama entrypoint: hash mismatch! re-downloading..."
        rm "$model_path"
        wget -c -O "$model_path" --progress=bar:force "$model_url" 2>&1
    fi
else
    echo "ollama entrypoint: model file not found. downloading..."
    wget -c -O "$model_path" --progress=bar:force "$model_url" 2>&1
fi

final_sha256=$(sha256sum "$model_path" | awk '{print $1}')
if [ "$final_sha256" != "$expected_sha256" ]; then
    echo "ollama entrypoint: ❌ fatal error: hash mismatch after download!"
    exit 1
fi
echo "ollama entrypoint: model is ready."

echo "ollama entrypoint: starting ollama serve in background..."
ollama serve &
pid=$!

sleep 5

echo "ollama entrypoint: creating model 'saiga-mistral' from file..."
ollama create saiga-mistral -f /Modelfile

echo "ollama entrypoint: setup complete. bringing ollama serve to foreground."
kill $pid
wait $pid 2>/dev/null

exec ollama serve