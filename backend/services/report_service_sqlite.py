"""Report generation service with SQLite support"""
from typing import Dict, Any, Optional
import json
import logging
from datetime import datetime

from utils.database import get_async_db, PatientRecord, AgentResultRecord
from models.btrads import BTRADSResult

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating and managing reports using SQLite"""
    
    async def get_patient_summary(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive patient summary including all results"""
        async with get_async_db() as db:
            try:
                # Get patient data
                patient = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
                
                if not patient:
                    return None
                
                # Get all agent results
                agent_results = db.query(AgentResultRecord).filter(
                    AgentResultRecord.patient_id == patient_id
                ).order_by(AgentResultRecord.timestamp.desc()).all()
                
                # Parse and format results
                results_by_node = {}
                for result in agent_results:
                    node_id = result.node_id
                    if node_id not in results_by_node:
                        results_by_node[node_id] = []
                    
                    results_by_node[node_id].append({
                        "agent_id": result.agent_id,
                        "extracted_value": json.loads(result.extracted_value) if result.extracted_value else None,
                        "confidence": result.confidence,
                        "reasoning": result.reasoning,
                        "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                        "validation_status": result.validation_status,
                        "validated_value": json.loads(result.validated_value) if result.validated_value else None
                    })
                
                # Build summary
                summary = {
                    "patient_id": patient.id,
                    "created_at": patient.created_at.isoformat() if patient.created_at else None,
                    "updated_at": patient.updated_at.isoformat() if patient.updated_at else None,
                    "processing_status": patient.processing_status,
                    "current_node": patient.current_node,
                    "completed": patient.completed,
                    "data": {
                        "clinical_note": patient.clinical_note[:500] + "..." if len(patient.clinical_note) > 500 else patient.clinical_note,
                        "baseline_date": patient.baseline_date.isoformat() if patient.baseline_date else None,
                        "followup_date": patient.followup_date.isoformat() if patient.followup_date else None,
                        "radiation_date": patient.radiation_date.isoformat() if patient.radiation_date else None,
                        "flair_change_percentage": patient.flair_change_percentage,
                        "enhancement_change_percentage": patient.enhancement_change_percentage,
                        "ground_truth_btrads": patient.ground_truth_btrads
                    },
                    "btrads_result": json.loads(patient.btrads_result) if patient.btrads_result else None,
                    "agent_results": results_by_node,
                    "validation_result": json.loads(patient.validation_result) if patient.validation_result else None,
                    "user_corrections": json.loads(patient.user_corrections) if patient.user_corrections else None
                }
                
                return summary
                
            except Exception as e:
                logger.error(f"Error getting patient summary: {e}")
                return None
    
    async def get_full_report(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get full patient report with clinical note and all details"""
        async with get_async_db() as db:
            try:
                # Get patient data
                patient = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
                
                if not patient:
                    return None
                
                # Get all agent results
                agent_results = db.query(AgentResultRecord).filter(
                    AgentResultRecord.patient_id == patient_id
                ).order_by(AgentResultRecord.timestamp.desc()).all()
                
                # Build full report
                report = {
                    "patient_id": patient.id,
                    "report_generated_at": datetime.utcnow().isoformat(),
                    "patient_data": {
                        "clinical_note": patient.clinical_note,
                        "baseline_date": patient.baseline_date.isoformat() if patient.baseline_date else None,
                        "followup_date": patient.followup_date.isoformat() if patient.followup_date else None,
                        "radiation_date": patient.radiation_date.isoformat() if patient.radiation_date else None,
                        "baseline_flair_volume": patient.baseline_flair_volume,
                        "followup_flair_volume": patient.followup_flair_volume,
                        "flair_change_percentage": patient.flair_change_percentage,
                        "baseline_enhancement_volume": patient.baseline_enhancement_volume,
                        "followup_enhancement_volume": patient.followup_enhancement_volume,
                        "enhancement_change_percentage": patient.enhancement_change_percentage
                    },
                    "btrads_assessment": json.loads(patient.btrads_result) if patient.btrads_result else None,
                    "ground_truth": patient.ground_truth_btrads,
                    "processing_details": {
                        "status": patient.processing_status,
                        "completed": patient.completed,
                        "current_node": patient.current_node,
                        "created_at": patient.created_at.isoformat() if patient.created_at else None,
                        "updated_at": patient.updated_at.isoformat() if patient.updated_at else None
                    },
                    "agent_extractions": [],
                    "validation_history": json.loads(patient.validation_history) if patient.validation_history else [],
                    "user_corrections": json.loads(patient.user_corrections) if patient.user_corrections else None
                }
                
                # Add agent results with full details
                for result in agent_results:
                    extraction = {
                        "node_id": result.node_id,
                        "agent_id": result.agent_id,
                        "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                        "extracted_value": json.loads(result.extracted_value) if result.extracted_value else None,
                        "confidence": result.confidence,
                        "reasoning": result.reasoning,
                        "source_highlights": json.loads(result.source_highlights) if result.source_highlights else [],
                        "validation_status": result.validation_status,
                        "validated_value": json.loads(result.validated_value) if result.validated_value else None,
                        "validator_notes": result.validator_notes,
                        "processing_time_ms": result.processing_time_ms,
                        "llm_model": result.llm_model
                    }
                    report["agent_extractions"].append(extraction)
                
                return report
                
            except Exception as e:
                logger.error(f"Error getting full report: {e}")
                return None
    
    async def generate_validation_report(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Generate validation report comparing extracted vs validated values"""
        async with get_async_db() as db:
            try:
                # Get all agent results
                agent_results = db.query(AgentResultRecord).filter(
                    AgentResultRecord.patient_id == patient_id
                ).all()
                
                if not agent_results:
                    return None
                
                # Analyze validation status
                total_results = len(agent_results)
                validated_results = [r for r in agent_results if r.validation_status == "validated"]
                pending_results = [r for r in agent_results if r.validation_status == "pending"]
                rejected_results = [r for r in agent_results if r.validation_status == "rejected"]
                
                # Build validation report
                report = {
                    "patient_id": patient_id,
                    "report_generated_at": datetime.utcnow().isoformat(),
                    "summary": {
                        "total_extractions": total_results,
                        "validated": len(validated_results),
                        "pending": len(pending_results),
                        "rejected": len(rejected_results),
                        "validation_rate": len(validated_results) / total_results if total_results > 0 else 0
                    },
                    "validations": []
                }
                
                # Add detailed validation comparisons
                for result in agent_results:
                    validation = {
                        "node_id": result.node_id,
                        "agent_id": result.agent_id,
                        "validation_status": result.validation_status,
                        "extracted_value": json.loads(result.extracted_value) if result.extracted_value else None,
                        "validated_value": json.loads(result.validated_value) if result.validated_value else None,
                        "changed": result.extracted_value != result.validated_value if result.validated_value else False,
                        "validator_notes": result.validator_notes,
                        "validated_by": result.validated_by,
                        "validated_at": result.validated_at.isoformat() if result.validated_at else None
                    }
                    report["validations"].append(validation)
                
                return report
                
            except Exception as e:
                logger.error(f"Error generating validation report: {e}")
                return None


# Create singleton instance
report_service = ReportService()