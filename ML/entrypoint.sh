#!/bin/sh

set -e

model_url="https://huggingface.co/ilyagusev/saiga_mistral_7b_gguf/resolve/main/model-q4_k.gguf"
model_dir="/models"
model_filename="model-q4_k.gguf"
model_path="$model_dir/$model_filename"
expected_sha256="3aa8925500d81ba2555364b611681a976c48324e3a89a5a7f457755b72e128b5"

echo "entrypoint: checking for language model..."

mkdir -p "$model_dir"

if [ -f "$model_path" ]; then
    echo "entrypoint: model file found. verifying sha256 hash..."
    current_sha256=$(sha256sum "$model_path" | awk '{print $1}')

    if [ "$current_sha256" = "$expected_sha256" ]; then
        echo "entrypoint: sha256 hash matches. skipping download."
    else
        echo "entrypoint: hash mismatch! re-downloading..."
        rm "$model_path"
        wget -o "$model_path" "$model_url"
    fi
else
    echo "entrypoint: model file not found. downloading..."
    wget -o "$model_path" "$model_url"
fi

echo "entrypoint: final hash check..."
final_sha256=$(sha256sum "$model_path" | awk '{print $1}')
if [ "$final_sha256" != "$expected_sha256" ]; then
    echo "entrypoint: fatal error: hash mismatch after download!"
    exit 1
fi
echo "entrypoint: model is ready."

echo "entrypoint: starting main application..."
exec "$@"