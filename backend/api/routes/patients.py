"""Patient management API routes"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
import pandas as pd
import io

from models.patient import Patient, PatientData

router = APIRouter()

# Will be set by main.py
patient_service = None

def set_patient_service(service):
    """Set the patient service instance"""
    global patient_service
    patient_service = service

@router.post("/", response_model=Patient)
async def create_patient(patient_data: PatientData):
    """Create a new patient"""
    return await patient_service.create_patient(patient_data)

@router.post("/upload", response_model=List[Patient])
async def upload_patients(file: UploadFile = File(...)):
    """Upload CSV file with patient data"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "File must be CSV format")
    
    try:
        # Read CSV
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Process and store patients
        patients = await patient_service.process_csv(df)
        return patients
        
    except Exception as e:
        raise HTTPException(400, f"Error processing file: {str(e)}")

@router.get("/", response_model=List[Patient])
async def list_patients(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
):
    """List all patients with optional filtering"""
    return await patient_service.list_patients(skip, limit, status)

@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str):
    """Get a specific patient"""
    patient = await patient_service.get_patient(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    return patient

@router.post("/{patient_id}/process")
async def start_processing(patient_id: str, auto_validate: bool = False):
    """Start processing a patient through BT-RADS flowchart"""
    patient = await patient_service.get_patient(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    
    # Start async processing
    await patient_service.start_processing(patient_id, auto_validate)
    
    return {"message": "Processing started", "patient_id": patient_id}

@router.get("/{patient_id}/status")
async def get_processing_status(patient_id: str):
    """Get current processing status for a patient"""
    status = await patient_service.get_processing_status(patient_id)
    if not status:
        raise HTTPException(404, "Patient not found")
    return status