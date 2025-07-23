"""Validation service for agent results"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from utils.database import get_async_db
from agents.orchestration.agent_orchestrator import AgentOrchestrator

class ValidationService:
    """Service for managing validation operations"""
    
    def __init__(self):
        self.orchestrator: Optional[AgentOrchestrator] = None
    
    def set_orchestrator(self, orchestrator: AgentOrchestrator):
        """Set the agent orchestrator"""
        self.orchestrator = orchestrator
    
    async def validate_result(
        self,
        patient_id: str,
        validation_id: str,
        validated_value: Any,
        notes: Optional[str] = None,
        validator_id: str = "system"
    ) -> Dict[str, Any]:
        """Validate an agent result"""
        if not self.orchestrator:
            raise ValueError("Orchestrator not initialized")
        
        # Update database
        async with get_async_db() as conn:
            # Find the result
            query = """
                UPDATE agent_results 
                SET validation_status = 'approved',
                    validated_value = $2,
                    validator_notes = $3,
                    validated_by = $4,
                    validated_at = $5
                WHERE patient_id = $1
                AND validation_status = 'pending'
                ORDER BY timestamp DESC
                LIMIT 1
                RETURNING id, node_id
            """
            
            row = await conn.fetchrow(
                query,
                patient_id,
                validated_value,
                notes,
                validator_id,
                datetime.utcnow()
            )
            
            if not row:
                raise ValueError("No pending validation found")
            
            # Notify orchestrator
            await self.orchestrator.validate_result(
                patient_id,
                validation_id,
                validated_value,
                notes
            )
            
            return {
                "id": row['id'],
                "node_id": row['node_id'],
                "validated_value": validated_value,
                "validator_id": validator_id
            }
    
    async def override_decision(
        self,
        patient_id: str,
        node_id: str,
        new_value: Any,
        reason: Optional[str] = None,
        override_by: str = "system"
    ) -> Dict[str, Any]:
        """Override a decision at a specific node"""
        async with get_async_db() as conn:
            # Update the most recent result for this node
            query = """
                UPDATE agent_results 
                SET validation_status = 'modified',
                    validated_value = $3,
                    validator_notes = $4,
                    validated_by = $5,
                    validated_at = $6
                WHERE patient_id = $1 AND node_id = $2
                ORDER BY timestamp DESC
                LIMIT 1
                RETURNING id, extracted_value
            """
            
            row = await conn.fetchrow(
                query,
                patient_id,
                node_id,
                new_value,
                reason,
                override_by,
                datetime.utcnow()
            )
            
            if not row:
                raise ValueError(f"No result found for node {node_id}")
            
            return {
                "id": row['id'],
                "node_id": node_id,
                "original_value": row['extracted_value'],
                "new_value": new_value,
                "override_by": override_by
            }
    
    async def get_pending_validations(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all pending validations for a patient"""
        async with get_async_db() as conn:
            query = """
                SELECT id, node_id, agent_id, extracted_value, 
                       confidence, reasoning, timestamp
                FROM agent_results
                WHERE patient_id = $1 AND validation_status = 'pending'
                ORDER BY timestamp ASC
            """
            
            rows = await conn.fetch(query, patient_id)
            
            validations = []
            for row in rows:
                validations.append({
                    "id": row['id'],
                    "node_id": row['node_id'],
                    "agent_id": row['agent_id'],
                    "extracted_value": row['extracted_value'],
                    "confidence": row['confidence'],
                    "reasoning": row['reasoning'],
                    "timestamp": row['timestamp'].isoformat()
                })
            
            return validations