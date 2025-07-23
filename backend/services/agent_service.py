"""Agent service for managing agent operations"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio

from utils.database import get_async_db, AgentResultRecord
from models.agent import AgentResult

class AgentService:
    """Service for managing agent operations"""
    
    async def get_results(
        self,
        patient_id: str,
        agent_id: Optional[str] = None,
        node_id: Optional[str] = None,
        validation_status: Optional[str] = None
    ) -> List[AgentResult]:
        """Get agent results with filtering"""
        async with get_async_db() as conn:
            query = "SELECT * FROM agent_results WHERE patient_id = $1"
            params = [patient_id]
            param_count = 1
            
            if agent_id:
                param_count += 1
                query += f" AND agent_id = ${param_count}"
                params.append(agent_id)
            
            if node_id:
                param_count += 1
                query += f" AND node_id = ${param_count}"
                params.append(node_id)
            
            if validation_status:
                param_count += 1
                query += f" AND validation_status = ${param_count}"
                params.append(validation_status)
            
            query += " ORDER BY timestamp DESC"
            
            rows = await conn.fetch(query, *params)
            
            results = []
            for row in rows:
                result = AgentResult(
                    agent_id=row['agent_id'],
                    node_id=row['node_id'],
                    patient_id=row['patient_id'],
                    timestamp=row['timestamp'],
                    extracted_value=row['extracted_value'],
                    confidence=row['confidence'],
                    reasoning=row['reasoning'],
                    source_highlights=row['source_highlights'] or [],
                    validation_status=row['validation_status'],
                    validated_value=row['validated_value'],
                    validator_notes=row['validator_notes'],
                    validated_by=row['validated_by'],
                    validated_at=row['validated_at'],
                    missing_info=row['missing_info'] or [],
                    processing_time_ms=row['processing_time_ms'],
                    llm_model=row['llm_model']
                )
                results.append(result)
            
            return results
    
    async def get_result_by_id(self, result_id: int) -> Optional[AgentResult]:
        """Get a specific agent result by ID"""
        async with get_async_db() as conn:
            query = "SELECT * FROM agent_results WHERE id = $1"
            row = await conn.fetchrow(query, result_id)
            
            if not row:
                return None
            
            return AgentResult(
                agent_id=row['agent_id'],
                node_id=row['node_id'],
                patient_id=row['patient_id'],
                timestamp=row['timestamp'],
                extracted_value=row['extracted_value'],
                confidence=row['confidence'],
                reasoning=row['reasoning'],
                source_highlights=row['source_highlights'] or [],
                validation_status=row['validation_status'],
                validated_value=row['validated_value'],
                validator_notes=row['validator_notes'],
                validated_by=row['validated_by'],
                validated_at=row['validated_at'],
                missing_info=row['missing_info'] or [],
                processing_time_ms=row['processing_time_ms'],
                llm_model=row['llm_model']
            )
    
    async def test_agent(
        self,
        agent_id: str,
        clinical_note: str,
        context: Dict[str, Any]
    ) -> AgentResult:
        """Test an agent with sample data"""
        # Import agent classes
        from agents.extraction.prior_assessment import PriorAssessmentAgent
        from agents.extraction.imaging_comparison import ImagingComparisonAgent
        
        # Map agent IDs to classes
        agent_map = {
            "prior_assessment_agent": PriorAssessmentAgent,
            "imaging_comparison_agent": ImagingComparisonAgent,
            # Add more agents as implemented
        }
        
        if agent_id not in agent_map:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        # Create agent instance
        agent_class = agent_map[agent_id]
        agent = agent_class()
        
        # Run extraction
        result = await agent.extract(
            clinical_note=clinical_note,
            context=context,
            patient_id="test_patient"
        )
        
        return result
    
    async def get_agent_performance(
        self,
        agent_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get performance metrics for an agent"""
        async with get_async_db() as conn:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get total runs
            total_query = """
                SELECT COUNT(*) as total,
                       AVG(confidence) as avg_confidence,
                       AVG(processing_time_ms) as avg_time
                FROM agent_results
                WHERE agent_id = $1 AND timestamp >= $2
            """
            
            total_row = await conn.fetchrow(total_query, agent_id, start_date)
            
            # Get validation stats
            validation_query = """
                SELECT validation_status, COUNT(*) as count
                FROM agent_results
                WHERE agent_id = $1 AND timestamp >= $2
                GROUP BY validation_status
            """
            
            validation_rows = await conn.fetch(validation_query, agent_id, start_date)
            validation_stats = {row['validation_status']: row['count'] for row in validation_rows}
            
            # Get error rate
            error_query = """
                SELECT COUNT(*) as error_count
                FROM agent_results
                WHERE agent_id = $1 AND timestamp >= $2 
                AND extracted_value = 'error'
            """
            
            error_row = await conn.fetchrow(error_query, agent_id, start_date)
            
            # Calculate metrics
            total = total_row['total'] or 0
            error_count = error_row['error_count'] or 0
            
            return {
                "agent_id": agent_id,
                "period_days": days,
                "total_runs": total,
                "avg_confidence": float(total_row['avg_confidence'] or 0),
                "avg_processing_time_ms": float(total_row['avg_time'] or 0),
                "validation_stats": validation_stats,
                "error_rate": error_count / total if total > 0 else 0,
                "success_rate": (total - error_count) / total if total > 0 else 0
            }