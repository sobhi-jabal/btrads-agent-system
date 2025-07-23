#!/usr/bin/env python3
"""Mock BT-RADS Backend for Testing"""

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import csv
import io
from typing import List
from datetime import datetime

app = FastAPI(title="BT-RADS Mock Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock patient data storage
mock_patients = []

@app.get("/")
async def root():
    return {
        "message": "BT-RADS Multi-Agent System API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "BT-RADS Mock Backend"
    }

@app.post("/api/patients/upload")
async def upload_patients(file: UploadFile = File(...)):
    """Upload endpoint that parses CSV and creates patient records"""
    global mock_patients
    
    # Read the file content
    content = await file.read()
    content_str = content.decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(content_str))
    
    # Clear existing mock patients
    mock_patients = []
    
    # Column mapping (from frontend validation)
    column_mapping = {
        'pid': 'patient_id',
        'clinical_note_closest': 'clinical_note',
        'Baseline_imaging_date': 'baseline_date',
        'Followup_imaging_date': 'followup_date',
        'Baseline_flair_volume': 'baseline_flair_volume',
        'Followup_flair_volume': 'followup_flair_volume',
        'Volume_Difference_flair_Percentage_Change': 'flair_change_percentage',
        'Baseline_enhancement_volume': 'baseline_enhancement_volume', 
        'Followup_enhancement_volume': 'followup_enhancement_volume',
        'Volume_Difference_enhancement_Percentage_Change': 'enhancement_change_percentage',
        'Ground_Truth_BTRADS (General Category)': 'ground_truth_btrads'
    }
    
    # Process each row
    for idx, row in enumerate(csv_reader):
        # Map CSV columns to patient data fields
        patient_data = {}
        for csv_col, field_name in column_mapping.items():
            if csv_col in row:
                value = row[csv_col]
                # Clean up the value
                if value and value.strip():
                    # For dates, try to parse them
                    if 'date' in field_name and '/' in value:
                        # Convert MM/DD/YYYY to YYYY-MM-DD
                        try:
                            parts = value.split('/')
                            if len(parts) == 3:
                                value = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                        except:
                            pass
                    patient_data[field_name] = value
        
        # Create patient record
        patient = {
            "id": f"PAT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{idx:03d}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "data": patient_data,
            "processing_status": "pending",
            "completed": False
        }
        
        # Only add if we have at least patient_id and clinical_note
        if patient_data.get('patient_id') and patient_data.get('clinical_note'):
            mock_patients.append(patient)
    
    print(f"Received file: {file.filename}")
    print(f"Parsed {len(mock_patients)} patients from CSV")
    
    return mock_patients

@app.post("/api/patients/")
async def create_patient(patient_data: dict):
    """Create a single patient"""
    patient = {
        "id": f"PAT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "data": patient_data,
        "processing_status": "pending",
        "completed": False
    }
    mock_patients.append(patient)
    return patient

@app.get("/api/patients")
async def list_patients():
    """List all patients"""
    return mock_patients

@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str):
    """Get a specific patient"""
    for patient in mock_patients:
        if patient["id"] == patient_id:
            return patient
    return {"error": "Patient not found"}

@app.post("/api/patients/{patient_id}/process")
async def start_processing(patient_id: str):
    """Start processing a patient"""
    for patient in mock_patients:
        if patient["id"] == patient_id:
            patient["processing_status"] = "processing"
            return {"message": "Processing started", "patient_id": patient_id}
    return {"error": "Patient not found"}

@app.get("/api/patients/{patient_id}/status")
async def get_status(patient_id: str):
    """Get processing status"""
    for patient in mock_patients:
        if patient["id"] == patient_id:
            return {
                "patient_id": patient_id,
                "status": patient["processing_status"],
                "completed": patient["completed"]
            }
    return {"error": "Patient not found"}

if __name__ == "__main__":
    print("Starting BT-RADS Mock Backend on http://localhost:8000")
    print("API Documentation available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)