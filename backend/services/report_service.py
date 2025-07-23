"""Report generation service"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from io import BytesIO

from utils.database import get_async_db
from models.btrads import BTRADSResult

class ReportService:
    """Service for generating reports"""
    
    async def generate_summary(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Generate a summary report for a patient"""
        async with get_async_db() as conn:
            # Get patient data
            patient_query = "SELECT * FROM patients WHERE id = $1"
            patient_row = await conn.fetchrow(patient_query, patient_id)
            
            if not patient_row or not patient_row['completed']:
                return None
            
            # Get agent results
            results_query = """
                SELECT node_id, extracted_value, validated_value, 
                       confidence, validation_status
                FROM agent_results
                WHERE patient_id = $1
                ORDER BY timestamp
            """
            result_rows = await conn.fetch(results_query, patient_id)
            
            # Parse BT-RADS result
            btrads_result = json.loads(patient_row['btrads_result']) if patient_row['btrads_result'] else None
            
            # Build summary
            summary = {
                "patient_id": patient_id,
                "processing_completed": patient_row['completed'],
                "btrads_score": btrads_result['score'] if btrads_result else None,
                "reasoning": btrads_result['reasoning'] if btrads_result else None,
                "confidence_score": btrads_result['confidence_score'] if btrads_result else None,
                "volume_data": {
                    "flair_change": patient_row['flair_change_percentage'],
                    "enhancement_change": patient_row['enhancement_change_percentage']
                },
                "timeline": {
                    "baseline_date": patient_row['baseline_date'].isoformat() if patient_row['baseline_date'] else None,
                    "followup_date": patient_row['followup_date'].isoformat() if patient_row['followup_date'] else None,
                    "radiation_date": patient_row['radiation_date'].isoformat() if patient_row['radiation_date'] else None
                },
                "node_results": [
                    {
                        "node_id": row['node_id'],
                        "extracted_value": row['extracted_value'],
                        "validated_value": row['validated_value'],
                        "confidence": row['confidence'],
                        "validation_status": row['validation_status']
                    }
                    for row in result_rows
                ],
                "ground_truth": patient_row['ground_truth_btrads']
            }
            
            return summary
    
    async def generate_pdf_report(self, patient_id: str) -> bytes:
        """Generate a PDF report for a patient"""
        # In a real implementation, this would use a PDF library like reportlab
        # For now, return a placeholder
        summary = await self.generate_summary(patient_id)
        
        if not summary:
            raise ValueError("No results found for patient")
        
        # Placeholder PDF generation
        pdf_content = f"""
BT-RADS Assessment Report
========================

Patient ID: {patient_id}
Generated: {datetime.utcnow().isoformat()}

BT-RADS Score: {summary['btrads_score']}
Confidence: {summary['confidence_score']:.2%}

Reasoning:
{summary['reasoning']}

Volume Changes:
- FLAIR: {summary['volume_data']['flair_change']}%
- Enhancement: {summary['volume_data']['enhancement_change']}%

Timeline:
- Baseline: {summary['timeline']['baseline_date']}
- Follow-up: {summary['timeline']['followup_date']}
- Radiation: {summary['timeline']['radiation_date']}
"""
        
        return pdf_content.encode('utf-8')
    
    async def export_patient_data(
        self,
        patient_id: str,
        include_raw: bool = False
    ) -> Dict[str, Any]:
        """Export all patient data as JSON"""
        async with get_async_db() as conn:
            # Get all data
            patient_query = "SELECT * FROM patients WHERE id = $1"
            patient_row = await conn.fetchrow(patient_query, patient_id)
            
            results_query = "SELECT * FROM agent_results WHERE patient_id = $1 ORDER BY timestamp"
            result_rows = await conn.fetch(results_query, patient_id)
            
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "patient": {
                    "id": patient_row['id'],
                    "clinical_note": patient_row['clinical_note'] if include_raw else "[REDACTED]",
                    "baseline_date": patient_row['baseline_date'].isoformat() if patient_row['baseline_date'] else None,
                    "followup_date": patient_row['followup_date'].isoformat() if patient_row['followup_date'] else None,
                    "radiation_date": patient_row['radiation_date'].isoformat() if patient_row['radiation_date'] else None,
                    "volumes": {
                        "baseline_flair": patient_row['baseline_flair_volume'],
                        "followup_flair": patient_row['followup_flair_volume'],
                        "flair_change_pct": patient_row['flair_change_percentage'],
                        "baseline_enhancement": patient_row['baseline_enhancement_volume'],
                        "followup_enhancement": patient_row['followup_enhancement_volume'],
                        "enhancement_change_pct": patient_row['enhancement_change_percentage']
                    }
                },
                "results": {
                    "btrads_score": json.loads(patient_row['btrads_result'])['score'] if patient_row['btrads_result'] else None,
                    "algorithm_path": json.loads(patient_row['algorithm_path']) if patient_row['algorithm_path'] else None,
                    "completed": patient_row['completed']
                },
                "agent_results": [
                    {
                        "node_id": row['node_id'],
                        "agent_id": row['agent_id'],
                        "timestamp": row['timestamp'].isoformat(),
                        "extracted_value": row['extracted_value'],
                        "confidence": row['confidence'],
                        "validation_status": row['validation_status'],
                        "validated_value": row['validated_value']
                    }
                    for row in result_rows
                ]
            }
            
            return export_data
    
    async def get_audit_trail(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get complete audit trail for a patient"""
        async with get_async_db() as conn:
            # Get all events
            query = """
                SELECT 'extraction' as event_type, 
                       timestamp, node_id, agent_id,
                       extracted_value as value,
                       confidence,
                       'system' as user_id
                FROM agent_results
                WHERE patient_id = $1
                
                UNION ALL
                
                SELECT 'validation' as event_type,
                       validated_at as timestamp,
                       node_id,
                       agent_id,
                       validated_value as value,
                       NULL as confidence,
                       validated_by as user_id
                FROM agent_results
                WHERE patient_id = $1 AND validated_at IS NOT NULL
                
                ORDER BY timestamp
            """
            
            rows = await conn.fetch(query, patient_id)
            
            audit_trail = []
            for row in rows:
                audit_trail.append({
                    "event_type": row['event_type'],
                    "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                    "node_id": row['node_id'],
                    "agent_id": row['agent_id'],
                    "value": row['value'],
                    "confidence": row['confidence'],
                    "user_id": row['user_id']
                })
            
            return audit_trail
    
    async def generate_batch_summary(self, patient_ids: List[str]) -> Dict[str, Any]:
        """Generate summary statistics for multiple patients"""
        async with get_async_db() as conn:
            # Get completed patients
            query = """
                SELECT id, btrads_result, ground_truth_btrads
                FROM patients
                WHERE id = ANY($1) AND completed = true
            """
            
            rows = await conn.fetch(query, patient_ids)
            
            # Calculate statistics
            score_distribution = {}
            accuracy_stats = {"correct": 0, "total": 0}
            
            for row in rows:
                if row['btrads_result']:
                    result = json.loads(row['btrads_result'])
                    score = result['score']
                    score_distribution[score] = score_distribution.get(score, 0) + 1
                    
                    if row['ground_truth_btrads']:
                        accuracy_stats['total'] += 1
                        if score == row['ground_truth_btrads']:
                            accuracy_stats['correct'] += 1
            
            return {
                "total_patients": len(patient_ids),
                "completed_patients": len(rows),
                "score_distribution": score_distribution,
                "accuracy": accuracy_stats['correct'] / accuracy_stats['total'] if accuracy_stats['total'] > 0 else None,
                "accuracy_stats": accuracy_stats
            }
    
    async def get_system_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get system-wide statistics"""
        async with get_async_db() as conn:
            # Build date filter
            date_filter = ""
            params = []
            if start_date:
                params.append(start_date)
                date_filter += f" AND created_at >= ${len(params)}"
            if end_date:
                params.append(end_date)
                date_filter += f" AND created_at <= ${len(params)}"
            
            # Get patient stats
            patient_query = f"""
                SELECT 
                    COUNT(*) as total_patients,
                    COUNT(CASE WHEN completed = true THEN 1 END) as completed_patients,
                    AVG(CASE WHEN completed = true THEN 
                        EXTRACT(EPOCH FROM (updated_at - created_at)) / 60 
                    END) as avg_processing_time_minutes
                FROM patients
                WHERE 1=1 {date_filter}
            """
            
            patient_stats = await conn.fetchrow(patient_query, *params)
            
            # Get agent stats
            agent_query = f"""
                SELECT 
                    agent_id,
                    COUNT(*) as runs,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time_ms) as avg_time_ms
                FROM agent_results
                WHERE 1=1 {date_filter.replace('created_at', 'timestamp')}
                GROUP BY agent_id
            """
            
            agent_rows = await conn.fetch(agent_query, *params)
            
            return {
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "patients": {
                    "total": patient_stats['total_patients'],
                    "completed": patient_stats['completed_patients'],
                    "avg_processing_time_minutes": float(patient_stats['avg_processing_time_minutes'] or 0)
                },
                "agents": [
                    {
                        "agent_id": row['agent_id'],
                        "total_runs": row['runs'],
                        "avg_confidence": float(row['avg_confidence'] or 0),
                        "avg_processing_time_ms": float(row['avg_time_ms'] or 0)
                    }
                    for row in agent_rows
                ]
            }