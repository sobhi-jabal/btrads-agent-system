"""Patient data models"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date, datetime
from enum import Enum

class PatientData(BaseModel):
    """Patient data model"""
    patient_id: Optional[str] = None
    clinical_note: str
    baseline_date: date
    followup_date: date
    radiation_date: Optional[date] = None
    
    # Volume measurements
    baseline_flair_volume: Optional[float] = None
    followup_flair_volume: Optional[float] = None
    flair_change_percentage: Optional[float] = None
    
    baseline_enhancement_volume: Optional[float] = None
    followup_enhancement_volume: Optional[float] = None
    enhancement_change_percentage: Optional[float] = None
    
    # Ground truth (if available)
    ground_truth_btrads: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "PT001",
                "clinical_note": "Patient with glioblastoma...",
                "baseline_date": "2024-01-15",
                "followup_date": "2024-04-15",
                "radiation_date": "2024-02-01",
                "baseline_flair_volume": 45.2,
                "followup_flair_volume": 42.1,
                "flair_change_percentage": -6.9,
                "baseline_enhancement_volume": 12.3,
                "followup_enhancement_volume": 8.7,
                "enhancement_change_percentage": -29.3
            }
        }

class Patient(BaseModel):
    """Patient model for database"""
    id: str
    created_at: datetime
    updated_at: datetime
    data: PatientData
    processing_status: str = "pending"
    current_node: Optional[str] = None
    completed: bool = False
    
    @classmethod
    def from_db_record(cls, record):
        """Create Patient from database record"""
        patient_data = PatientData(
            patient_id=record.id,
            clinical_note=record.clinical_note,
            baseline_date=record.baseline_date,
            followup_date=record.followup_date,
            radiation_date=record.radiation_date,
            baseline_flair_volume=record.baseline_flair_volume,
            followup_flair_volume=record.followup_flair_volume,
            flair_change_percentage=record.flair_change_percentage,
            baseline_enhancement_volume=record.baseline_enhancement_volume,
            followup_enhancement_volume=record.followup_enhancement_volume,
            enhancement_change_percentage=record.enhancement_change_percentage,
            ground_truth_btrads=record.ground_truth_btrads
        )
        
        return cls(
            id=record.id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            data=patient_data,
            processing_status=record.processing_status,
            current_node=record.current_node,
            completed=record.completed
        )