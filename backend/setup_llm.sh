#!/bin/bash
# Setup script for BT-RADS LLM backend

echo "BT-RADS LLM Backend Setup"
echo "========================="

# Check Python version
python_version=$(python3 --version 2>&1)
echo "✓ Python version: $python_version"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check if Ollama is installed
if command -v ollama &> /dev/null; then
    echo ""
    echo "✓ Ollama is installed"
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama service is running"
    else
        echo "⚠ Ollama service is not running"
        echo "Starting Ollama..."
        ollama serve &
        sleep 3
    fi
    
    # Check for required model
    echo ""
    echo "Checking for required models..."
    if ollama list | grep -q "phi4:14b"; then
        echo "✓ Model phi4:14b is available"
    else
        echo "⚠ Model phi4:14b not found"
        echo "Pulling model (this may take a while)..."
        ollama pull phi4:14b
    fi
else
    echo ""
    echo "⚠ Ollama is not installed"
    echo "Please install Ollama first:"
    echo "  macOS: brew install ollama"
    echo "  Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "  Windows: Download from https://ollama.com/download"
    echo ""
    echo "The application requires Ollama to function."
    exit 1
fi

echo ""
echo "Setup complete!"
echo ""
echo "To start the backend:"
echo "  python btrads_backend.py"
echo ""
echo "To run tests:"
echo "  python test_llm_extraction.py"