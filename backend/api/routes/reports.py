"""Report generation API routes"""
from fastapi import APIRouter, HTTPException, Response
from typing import Optional
import json
import io
from datetime import datetime

from services.report_service import ReportService
from models.btrads import BTRADSResult

router = APIRouter()
report_service = ReportService()

@router.get("/{patient_id}/summary")
async def get_patient_summary(patient_id: str):
    """Get a summary report for a patient"""
    try:
        summary = await report_service.generate_summary(patient_id)
        if not summary:
            raise HTTPException(404, f"No results found for patient {patient_id}")
        return summary
    except Exception as e:
        raise HTTPException(500, f"Error generating summary: {str(e)}")

@router.get("/{patient_id}/pdf")
async def generate_pdf_report(patient_id: str):
    """Generate a PDF report for a patient"""
    try:
        pdf_bytes = await report_service.generate_pdf_report(patient_id)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=btrads_report_{patient_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(500, f"Error generating PDF: {str(e)}")

@router.get("/{patient_id}/export/json")
async def export_json(patient_id: str, include_raw: bool = False):
    """Export patient results as JSON"""
    try:
        data = await report_service.export_patient_data(
            patient_id,
            include_raw=include_raw
        )
        
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=btrads_export_{patient_id}.json"
            }
        )
    except Exception as e:
        raise HTTPException(500, f"Error exporting data: {str(e)}")

@router.get("/{patient_id}/audit-trail")
async def get_audit_trail(patient_id: str):
    """Get complete audit trail for a patient"""
    try:
        audit_trail = await report_service.get_audit_trail(patient_id)
        return {
            "patient_id": patient_id,
            "audit_trail": audit_trail,
            "total_events": len(audit_trail)
        }
    except Exception as e:
        raise HTTPException(500, f"Error retrieving audit trail: {str(e)}")

@router.post("/batch/summary")
async def generate_batch_summary(patient_ids: list[str]):
    """Generate summary statistics for multiple patients"""
    try:
        if not patient_ids:
            raise ValueError("No patient IDs provided")
        
        summary = await report_service.generate_batch_summary(patient_ids)
        return summary
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Error generating batch summary: {str(e)}")

@router.get("/statistics")
async def get_system_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get system-wide statistics"""
    try:
        stats = await report_service.get_system_statistics(start_date, end_date)
        return stats
    except Exception as e:
        raise HTTPException(500, f"Error calculating statistics: {str(e)}")