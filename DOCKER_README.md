# BT-RADS Multi-Agent System - Docker Setup

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop/))
- 8GB+ RAM available for Docker
- Ports 3000, 8000, 5432, 6379, and 11434 available

### One-Command Start

```bash
cd btrads-agent-system
./docker-run.sh
```

This will:
1. ✅ Build all containers
2. ✅ Start PostgreSQL, Redis, Ollama, Backend, and Frontend
3. ✅ Download required LLM models
4. ✅ Initialize the database
5. ✅ Open the browser automatically

## 📦 What's Included

### Services
- **Frontend** (port 3000): Next.js UI with React Flow visualization
- **Backend** (port 8000): FastAPI with agent orchestration
- **PostgreSQL** (port 5432): Patient data and results storage
- **Redis** (port 6379): Caching and session management
- **Ollama** (port 11434): Local LLM for agent processing

### Volumes
- `postgres_data`: Database persistence
- `ollama_data`: Model storage
- `backend_logs`: Application logs
- Code directories are mounted for hot-reloading

## 🎮 Usage Commands

### Start the system
```bash
./docker-run.sh
# or
./docker-run.sh start
```

### Rebuild containers (after code changes)
```bash
./docker-run.sh rebuild
```

### Stop the system
```bash
./docker-run.sh stop
```

### View logs
```bash
./docker-run.sh logs
# or for specific service
docker-compose logs -f backend
```

### Check status
```bash
./docker-run.sh status
```

### Clean everything (including data)
```bash
./docker-run.sh clean
```

## 🔧 Manual Docker Commands

### Start with docker-compose directly
```bash
docker-compose up -d
```

### Stop and remove containers
```bash
docker-compose down
```

### Rebuild a specific service
```bash
docker-compose build backend
docker-compose up -d backend
```

### Access container shell
```bash
# Backend
docker exec -it btrads-backend bash

# Database
docker exec -it btrads-postgres psql -U postgres -d btrads_db
```

## 🌐 Access Points

Once running, access the system at:
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: `postgresql://postgres:postgres123@localhost:5432/btrads_db`

## 📊 System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│    Frontend     │────▶│    Backend      │────▶│   PostgreSQL    │
│   (Port 3000)   │◀────│   (Port 8000)   │◀────│   (Port 5432)   │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        
         │                       ▼                        
         │              ┌─────────────────┐              
         │              │                 │              
         │              │     Ollama      │              
         │              │  (Port 11434)   │              
         │              │                 │              
         │              └─────────────────┘              
         │                       ▲                        
         │                       │                        
         └───── WebSocket ───────┘                        
                                                         
                        ┌─────────────────┐              
                        │                 │              
                        │      Redis      │              
                        │   (Port 6379)   │              
                        │                 │              
                        └─────────────────┘              
```

## 🐛 Troubleshooting

### Docker not running
```
❌ Docker daemon is not running. Please start Docker.
```
**Solution**: Start Docker Desktop

### Port already in use
```
Error: bind: address already in use
```
**Solution**: 
```bash
# Find process using port (example for 3000)
lsof -i :3000
# Kill the process
kill -9 <PID>
```

### Model download fails
```
Error pulling model
```
**Solution**: 
```bash
# Manually pull model
docker exec -it btrads-ollama ollama pull llama3:8b
```

### Database connection issues
```
could not connect to server: Connection refused
```
**Solution**: 
```bash
# Check if postgres is running
docker-compose ps postgres
# Restart postgres
docker-compose restart postgres
```

### Permission denied
```
Permission denied while trying to connect to Docker daemon
```
**Solution**: 
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Then logout and login again
```

## 🔐 Security Notes

- Default passwords are for development only
- Change `SECRET_KEY` in production
- Use environment files for sensitive data
- Enable HTTPS for production deployment

## 💾 Data Persistence

Data is persisted in Docker volumes:
- Database data survives container restarts
- Uploaded files and results are preserved
- To backup: `docker run --rm -v btrads-postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data`

## 🚀 Production Deployment

For production:
1. Update `.env` files with secure values
2. Use `docker-compose.prod.yml` configuration
3. Set up SSL/TLS certificates
4. Configure reverse proxy (Nginx/Traefik)
5. Enable container health monitoring
6. Set up automated backups

## 📝 Development Tips

### Hot Reload
- Frontend and backend code changes auto-reload
- No need to restart containers for code changes

### Adding Dependencies
```bash
# Backend
docker exec -it btrads-backend pip install <package>
# Then add to requirements.txt

# Frontend
docker exec -it btrads-frontend npm install <package>
# Then update package.json
```

### Database Migrations
```bash
docker exec -it btrads-backend alembic upgrade head
```

### Debugging
- Check logs: `docker-compose logs -f <service>`
- Use VSCode Docker extension for debugging
- Access container shell for troubleshooting