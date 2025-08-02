"""
BT-RADS Multi-Agent System - FastAPI Backend
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Dict
import asyncio

from api.routes import patients, agents, validation, reports, llm, vllm_extract
from services.websocket_manager import WebSocketManager
from services.patient_service import PatientService
from config.agent_config import agent_config
from utils.database import init_db
from utils.startup_checks import run_startup_checks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket manager instance
manager = WebSocketManager()

# Initialize patient service (singleton)
patient_service = PatientService()

# Initialize orchestrator based on configuration
OrchestratorClass = agent_config.get_orchestrator_class()
orchestrator = OrchestratorClass(manager)
patient_service.set_orchestrator(orchestrator)
logger.info(f"Using {OrchestratorClass.__name__} for orchestration")

# Set patient service in routes
patients.set_patient_service(patient_service)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting BT-RADS Multi-Agent System...")
    
    # Run startup checks
    startup_results = await run_startup_checks()
    
    if not startup_results["all_required_passed"]:
        logger.error("Required services are not available. Please check configuration.")
        # Continue anyway for development, but log warnings
    
    logger.info(f"System starting in {startup_results['agent_mode']} mode")
    
    # Initialize database
    # await init_db()  # Disabled for testing without PostgreSQL
    
    # Re-initialize orchestrator with correct agent mode
    global orchestrator
    OrchestratorClass = agent_config.get_orchestrator_class()
    orchestrator = OrchestratorClass(manager)
    patient_service.set_orchestrator(orchestrator)
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="BT-RADS Multi-Agent System",
    description="Interactive graph-based UI for BT-RADS classification with multi-agent validation",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(validation.router, prefix="/api/validation", tags=["validation"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(vllm_extract.router, prefix="/api/vllm", tags=["vllm"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "BT-RADS Multi-Agent System API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.websocket("/ws/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, patient_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            await manager.process_message(patient_id, data)
    except WebSocketDisconnect:
        manager.disconnect(patient_id)
        logger.info(f"Patient {patient_id} disconnected")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)