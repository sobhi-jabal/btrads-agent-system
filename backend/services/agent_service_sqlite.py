"""Agent service with SQLite support"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import logging

from models.agent import AgentResult, HighlightedSource
from utils.database import get_async_db, AgentResultRecord

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing agent results using SQLite"""
    
    async def get_results(
        self,
        patient_id: str,
        agent_id: Optional[str] = None,
        node_id: Optional[str] = None,
        validation_status: Optional[str] = None
    ) -> List[AgentResult]:
        """Get agent results with optional filtering"""
        async with get_async_db() as db:
            try:
                # Build query using SQLAlchemy
                query = db.query(AgentResultRecord)
                
                # Apply filters
                query = query.filter(AgentResultRecord.patient_id == patient_id)
                
                if agent_id:
                    query = query.filter(AgentResultRecord.agent_id == agent_id)
                
                if node_id:
                    query = query.filter(AgentResultRecord.node_id == node_id)
                
                if validation_status:
                    query = query.filter(AgentResultRecord.validation_status == validation_status)
                
                query = query.order_by(AgentResultRecord.timestamp.desc())
                
                records = query.all()
                
                results = []
                for record in records:
                    # Parse JSON fields
                    source_highlights = []
                    if record.source_highlights:
                        highlights_data = json.loads(record.source_highlights)
                        for h in highlights_data:
                            source_highlights.append(HighlightedSource(**h))
                    
                    result = AgentResult(
                        agent_id=record.agent_id,
                        node_id=record.node_id,
                        patient_id=record.patient_id,
                        timestamp=record.timestamp,
                        extracted_value=json.loads(record.extracted_value) if record.extracted_value else None,
                        confidence=record.confidence,
                        reasoning=record.reasoning,
                        source_highlights=source_highlights,
                        validation_status=record.validation_status,
                        validated_value=json.loads(record.validated_value) if record.validated_value else None,
                        validator_notes=record.validator_notes,
                        validated_by=record.validated_by,
                        validated_at=record.validated_at,
                        missing_info=json.loads(record.missing_info) if record.missing_info else [],
                        processing_time_ms=record.processing_time_ms,
                        llm_model=record.llm_model
                    )
                    results.append(result)
                
                return results
            except Exception as e:
                logger.error(f"Error fetching agent results: {e}")
                return []
    
    async def get_result_by_id(self, result_id: int) -> Optional[AgentResult]:
        """Get a specific agent result by ID"""
        async with get_async_db() as db:
            try:
                record = db.query(AgentResultRecord).filter(AgentResultRecord.id == result_id).first()
                
                if not record:
                    return None
                
                # Parse JSON fields
                source_highlights = []
                if record.source_highlights:
                    highlights_data = json.loads(record.source_highlights)
                    for h in highlights_data:
                        source_highlights.append(HighlightedSource(**h))
                
                return AgentResult(
                    agent_id=record.agent_id,
                    node_id=record.node_id,
                    patient_id=record.patient_id,
                    timestamp=record.timestamp,
                    extracted_value=json.loads(record.extracted_value) if record.extracted_value else None,
                    confidence=record.confidence,
                    reasoning=record.reasoning,
                    source_highlights=source_highlights,
                    validation_status=record.validation_status,
                    validated_value=json.loads(record.validated_value) if record.validated_value else None,
                    validator_notes=record.validator_notes,
                    validated_by=record.validated_by,
                    validated_at=record.validated_at,
                    missing_info=json.loads(record.missing_info) if record.missing_info else [],
                    processing_time_ms=record.processing_time_ms,
                    llm_model=record.llm_model
                )
            except Exception as e:
                logger.error(f"Error fetching agent result by ID: {e}")
                return None
    
    async def save_result(self, result: AgentResult) -> AgentResult:
        """Save an agent result"""
        async with get_async_db() as db:
            try:
                # Convert to database record
                record = AgentResultRecord(
                    agent_id=result.agent_id,
                    node_id=result.node_id,
                    patient_id=result.patient_id,
                    timestamp=result.timestamp or datetime.utcnow(),
                    extracted_value=json.dumps(result.extracted_value) if result.extracted_value else None,
                    confidence=result.confidence,
                    reasoning=result.reasoning,
                    source_highlights=json.dumps([h.model_dump() for h in result.source_highlights]) if result.source_highlights else None,
                    validation_status=result.validation_status,
                    validated_value=json.dumps(result.validated_value) if result.validated_value else None,
                    validator_notes=result.validator_notes,
                    validated_by=result.validated_by,
                    validated_at=result.validated_at,
                    missing_info=json.dumps(result.missing_info) if result.missing_info else None,
                    processing_time_ms=result.processing_time_ms,
                    llm_model=result.llm_model,
                    extra_metadata=None  # No metadata field in AgentResult model
                )
                
                db.add(record)
                db.commit()
                db.refresh(record)
                
                return result
            except Exception as e:
                logger.error(f"Error saving agent result: {e}")
                db.rollback()
                raise
    
    async def update_validation(
        self,
        result_id: int,
        validation_data: Dict[str, Any]
    ) -> Optional[AgentResult]:
        """Update validation for an agent result"""
        async with get_async_db() as db:
            try:
                record = db.query(AgentResultRecord).filter(AgentResultRecord.id == result_id).first()
                
                if not record:
                    return None
                
                # Update validation fields
                record.validation_status = validation_data.get("status", "validated")
                record.validated_value = json.dumps(validation_data.get("value"))
                record.validator_notes = validation_data.get("notes", "")
                record.validated_by = validation_data.get("validated_by", "user")
                record.validated_at = datetime.utcnow()
                
                db.commit()
                
                # Return updated result
                return await self.get_result_by_id(result_id)
            except Exception as e:
                logger.error(f"Error updating validation: {e}")
                db.rollback()
                return None


# Create singleton instance
agent_service = AgentService()