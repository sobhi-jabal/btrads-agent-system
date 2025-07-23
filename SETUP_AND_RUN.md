# BT-RADS Multi-Agent System - Setup & Run Guide

## Prerequisites

1. **Python 3.8+** - For backend
2. **Node.js 16+** - For frontend
3. **PostgreSQL** - Database (or use SQLite for development)
4. **Redis** - For caching (optional)
5. **Ollama** - For LLM functionality

### Installing Prerequisites

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install python@3.11 node postgresql redis

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install prerequisites
sudo apt install python3 python3-pip python3-venv nodejs npm postgresql redis-server

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

## Quick Start (Automated)

The easiest way to start the system:

```bash
cd btrads-agent-system
./start_system.sh
```

This script will:
1. Check prerequisites
2. Create virtual environments
3. Install dependencies
4. Start both backend and frontend
5. Open the browser automatically

## Manual Setup

### Backend Setup

1. **Navigate to backend directory**:
```bash
cd backend
```

2. **Create virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up database** (PostgreSQL):
```bash
# Create database
createdb btrads_db

# Or use PostgreSQL client
psql -U postgres
CREATE DATABASE btrads_db;
\q
```

5. **Configure environment**:
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
# For development, the defaults should work
```

6. **Download Ollama models**:
```bash
# Start Ollama service
ollama serve &

# Pull required models
ollama pull llama3:8b
ollama pull llama3:70b  # Optional, for better accuracy
```

7. **Start backend server**:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Frontend Setup

1. **Open new terminal and navigate to frontend**:
```bash
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Start development server**:
```bash
npm run dev
```

The frontend will be available at: http://localhost:3000

## Using the System

### 1. Upload Patient Data

1. Navigate to http://localhost:3000
2. Click "Upload Patients" button
3. Select your CSV file with patient data
4. Required CSV columns:
   - `patient_id` or `id`
   - `clinical_note`
   - `baseline_date` or `Baseline_imaging_date`
   - `followup_date` or `Followup_imaging_date`
   - Volume measurements (optional but recommended)

### 2. Process a Patient

1. Click on a patient from the list
2. You'll see the BT-RADS flowchart visualization
3. Click "Start Processing" to begin
4. The system will:
   - Progress through each node
   - Extract information using specialized agents
   - Pause for validation at each step
   - Highlight source evidence in the clinical note

### 3. Validate Results

At each validation point:
1. Review the extracted value
2. Check the highlighted source evidence
3. Either:
   - Click "Validate" to approve
   - Modify the value and add notes
   - Flag for review

### 4. Export Results

Once processing is complete:
1. Click "Export" to download:
   - PDF report with full assessment
   - JSON data for integration
   - Audit trail for compliance

## System Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Next.js   │────▶│   FastAPI   │────▶│ PostgreSQL  │
│   Frontend  │◀────│   Backend   │◀────│  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    
       │                    ▼                    
       │            ┌─────────────┐              
       │            │   Ollama    │              
       │            │     LLM     │              
       │            └─────────────┘              
       │                                         
       └──── WebSocket ─────┘                    
```

## Troubleshooting

### Backend Issues

1. **Port 8000 already in use**:
```bash
# Find and kill process
lsof -i :8000
kill -9 <PID>
```

2. **Database connection error**:
- Ensure PostgreSQL is running: `pg_ctl status`
- Check credentials in `.env`
- For development, you can use SQLite by changing DATABASE_URL

3. **Ollama not found**:
- Install Ollama: https://ollama.ai
- Ensure ollama service is running: `ollama serve`

### Frontend Issues

1. **Port 3000 already in use**:
```bash
# Find and kill process
lsof -i :3000
kill -9 <PID>
```

2. **Module not found errors**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### WebSocket Connection Issues

1. Check that both frontend and backend are running
2. Verify WebSocket URL in frontend `.env.local`
3. Check browser console for errors

## Development Tips

1. **Backend API Documentation**: http://localhost:8000/docs
2. **Frontend Hot Reload**: Changes automatically reflect
3. **Database Viewer**: Use pgAdmin or DBeaver
4. **Testing Agents**: Use the `/api/agents/test/{agent_id}` endpoint

## Production Deployment

For production deployment:

1. Use a production database (PostgreSQL)
2. Set secure environment variables
3. Use a process manager (PM2, systemd)
4. Set up reverse proxy (Nginx)
5. Enable HTTPS
6. Configure CORS properly

See `DEPLOYMENT.md` for detailed production setup instructions.