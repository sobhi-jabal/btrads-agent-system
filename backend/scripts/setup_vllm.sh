#!/bin/bash

echo "BT-RADS vLLM Setup Script"
echo "========================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for GPU support
check_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}✓ NVIDIA GPU detected${NC}"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
        return 0
    else
        echo -e "${YELLOW}⚠ No NVIDIA GPU detected. Will use CPU mode.${NC}"
        return 1
    fi
}

# Install vLLM
install_vllm() {
    echo "Installing vLLM..."
    
    if check_gpu; then
        # GPU installation
        pip install vllm>=0.4.0 --upgrade
        echo -e "${GREEN}✓ vLLM installed with GPU support${NC}"
    else
        # CPU installation
        pip install vllm-cpu>=0.4.0 --upgrade
        echo -e "${GREEN}✓ vLLM installed with CPU support${NC}"
    fi
}

# Download models
download_models() {
    echo "Downloading models..."
    
    # Create model directory
    mkdir -p ~/.cache/huggingface
    
    # Download models using huggingface-cli
    pip install huggingface-hub
    
    echo "Downloading Llama 3.1 8B (for testing)..."
    huggingface-cli download meta-llama/Meta-Llama-3.1-8B-Instruct \
        --local-dir ~/.cache/huggingface/models/llama-3.1-8b \
        --local-dir-use-symlinks False
    
    echo "Downloading BioMistral 7B..."
    huggingface-cli download BioMistral/BioMistral-7B \
        --local-dir ~/.cache/huggingface/models/biomistral-7b \
        --local-dir-use-symlinks False
    
    echo -e "${GREEN}✓ Models downloaded${NC}"
}

# Start vLLM server
start_vllm_server() {
    echo "Starting vLLM server..."
    
    if check_gpu; then
        # GPU server
        python -m vllm.entrypoints.openai.api_server \
            --model meta-llama/Meta-Llama-3.1-8B-Instruct \
            --host 0.0.0.0 \
            --port 8000 \
            --max-model-len 8192 \
            --gpu-memory-utilization 0.9 &
    else
        # CPU server (smaller model)
        python -m vllm.entrypoints.openai.api_server \
            --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
            --host 0.0.0.0 \
            --port 8000 \
            --max-model-len 2048 \
            --device cpu &
    fi
    
    VLLM_PID=$!
    echo "vLLM server started with PID: $VLLM_PID"
    
    # Wait for server to be ready
    echo "Waiting for server to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null; then
            echo -e "${GREEN}✓ vLLM server is ready!${NC}"
            break
        fi
        sleep 2
    done
}

# Test vLLM server
test_vllm_server() {
    echo "Testing vLLM server..."
    
    curl -X POST http://localhost:8000/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{
            "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is BT-RADS?"}
            ],
            "max_tokens": 100
        }' | python -m json.tool
}

# Main menu
main_menu() {
    echo ""
    echo "Select an option:"
    echo "1) Install vLLM"
    echo "2) Download models"
    echo "3) Start vLLM server"
    echo "4) Test vLLM server"
    echo "5) Full setup (all of the above)"
    echo "6) Exit"
    
    read -p "Enter your choice (1-6): " choice
    
    case $choice in
        1) install_vllm ;;
        2) download_models ;;
        3) start_vllm_server ;;
        4) test_vllm_server ;;
        5) 
            install_vllm
            download_models
            start_vllm_server
            test_vllm_server
            ;;
        6) exit 0 ;;
        *) echo -e "${RED}Invalid choice${NC}" ;;
    esac
}

# Run main menu
while true; do
    main_menu
done