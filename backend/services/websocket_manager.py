"""WebSocket connection manager for real-time updates"""
from typing import Dict, Any
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store active connections by patient_id
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, patient_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[patient_id] = websocket
        logger.info(f"WebSocket connected for patient {patient_id}")
        
        # Send initial connection confirmation
        await self.send_to_patient(patient_id, {
            "type": "connection_established",
            "patient_id": patient_id
        })
    
    def disconnect(self, patient_id: str):
        """Remove a WebSocket connection"""
        if patient_id in self.active_connections:
            del self.active_connections[patient_id]
            logger.info(f"WebSocket disconnected for patient {patient_id}")
    
    async def send_to_patient(self, patient_id: str, data: Dict[str, Any]):
        """Send data to a specific patient's WebSocket"""
        if patient_id in self.active_connections:
            websocket = self.active_connections[patient_id]
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error sending to patient {patient_id}: {str(e)}")
                self.disconnect(patient_id)
    
    async def broadcast(self, data: Dict[str, Any]):
        """Broadcast data to all connected clients"""
        disconnected = []
        for patient_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to patient {patient_id}: {str(e)}")
                disconnected.append(patient_id)
        
        # Clean up disconnected clients
        for patient_id in disconnected:
            self.disconnect(patient_id)
    
    async def process_message(self, patient_id: str, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            # Handle different message types
            if message_type == "ping":
                await self.send_to_patient(patient_id, {"type": "pong"})
            elif message_type == "validation_response":
                # This would be handled by the orchestrator
                pass
            else:
                logger.warning(f"Unknown message type from {patient_id}: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from patient {patient_id}: {message}")
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def is_connected(self, patient_id: str) -> bool:
        """Check if a patient is connected"""
        return patient_id in self.active_connections