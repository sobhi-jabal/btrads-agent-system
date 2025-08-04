# BT-RADS Multi-Agent System Makefile

.PHONY: help start stop restart logs setup-models clean build

help:
	@echo "Available commands:"
	@echo "  make start         - Start all services"
	@echo "  make stop          - Stop all services"
	@echo "  make restart       - Restart all services"
	@echo "  make logs          - Show logs from all services"
	@echo "  make setup-models  - Download phi4 model"
	@echo "  make clean         - Remove all containers and volumes"
	@echo "  make build         - Build all images"

start:
	docker-compose up -d

stop:
	docker-compose down

restart: stop start

logs:
	docker-compose logs -f

setup-models:
	docker-compose --profile setup up model-downloader

clean:
	docker-compose down -v
	docker system prune -f

build:
	docker-compose build

# Development helpers
backend-logs:
	docker-compose logs -f backend

frontend-logs:
	docker-compose logs -f frontend

ollama-logs:
	docker-compose logs -f ollama

# Test Ollama
test-ollama:
	@echo "Testing Ollama with phi4..."
	@curl -X POST http://localhost:11434/api/generate \
		-H "Content-Type: application/json" \
		-d '{"model": "phi4:14b", "prompt": "Hello", "stream": false}' | jq