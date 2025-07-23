#!/bin/bash

# BT-RADS Docker Runner Script

set -e

echo "🚀 Starting BT-RADS Multi-Agent System with Docker..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    # Try docker compose (newer syntax)
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed.${NC}"
        exit 1
    fi
    # Use newer syntax
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running. Please start Docker.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is ready${NC}"

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=0

    echo -e "${BLUE}⏳ Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $service_name is ready${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    echo -e "${RED}❌ $service_name failed to start${NC}"
    return 1
}

# Parse command line arguments
COMMAND=${1:-"up"}
REBUILD=""

if [ "$1" == "rebuild" ]; then
    COMMAND="up"
    REBUILD="--build"
fi

case $COMMAND in
    "up"|"start")
        echo -e "${BLUE}📦 Building and starting containers...${NC}"
        
        # Start all services
        $COMPOSE_CMD up -d $REBUILD
        
        # Wait for services to be ready
        echo -e "\n${BLUE}🔍 Checking service health...${NC}"
        
        wait_for_service "Backend API" "http://localhost:8000"
        wait_for_service "Frontend UI" "http://localhost:3000"
        
        # Download Ollama models if needed
        echo -e "\n${BLUE}📥 Checking Ollama models...${NC}"
        if ! docker exec btrads-ollama ollama list | grep -q "llama3:8b"; then
            echo -e "${YELLOW}Downloading llama3:8b model (this may take a few minutes)...${NC}"
            docker exec btrads-ollama ollama pull llama3:8b
            echo -e "${GREEN}✓ Model downloaded${NC}"
        else
            echo -e "${GREEN}✓ Models already available${NC}"
        fi
        
        echo -e "\n${GREEN}🎉 BT-RADS System is ready!${NC}"
        echo -e "\n📍 Access points:"
        echo -e "  - Frontend UI: ${BLUE}http://localhost:3000${NC}"
        echo -e "  - Backend API: ${BLUE}http://localhost:8000${NC}"
        echo -e "  - API Docs: ${BLUE}http://localhost:8000/docs${NC}"
        echo -e "\n💡 To view logs: ${YELLOW}$COMPOSE_CMD logs -f${NC}"
        echo -e "💡 To stop: ${YELLOW}./docker-run.sh stop${NC}"
        
        # Open browser
        if command -v open &> /dev/null; then
            sleep 2
            open http://localhost:3000
        elif command -v xdg-open &> /dev/null; then
            sleep 2
            xdg-open http://localhost:3000
        fi
        ;;
        
    "stop"|"down")
        echo -e "${YELLOW}🛑 Stopping containers...${NC}"
        $COMPOSE_CMD down
        echo -e "${GREEN}✓ All containers stopped${NC}"
        ;;
        
    "restart")
        echo -e "${YELLOW}🔄 Restarting containers...${NC}"
        $COMPOSE_CMD restart
        ;;
        
    "logs")
        $COMPOSE_CMD logs -f
        ;;
        
    "clean")
        echo -e "${RED}🧹 Cleaning up everything (including volumes)...${NC}"
        echo -e "${YELLOW}⚠️  This will delete all data. Continue? (y/N)${NC}"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            $COMPOSE_CMD down -v --remove-orphans
            echo -e "${GREEN}✓ Cleanup complete${NC}"
        else
            echo "Cleanup cancelled"
        fi
        ;;
        
    "status")
        echo -e "${BLUE}📊 Container status:${NC}"
        $COMPOSE_CMD ps
        ;;
        
    *)
        echo "Usage: ./docker-run.sh [command]"
        echo ""
        echo "Commands:"
        echo "  up, start    - Start all services"
        echo "  rebuild      - Rebuild and start all services"
        echo "  stop, down   - Stop all services"
        echo "  restart      - Restart all services"
        echo "  logs         - Show logs (follow mode)"
        echo "  clean        - Remove all containers and volumes"
        echo "  status       - Show container status"
        ;;
esac