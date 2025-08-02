#!/usr/bin/env python3
"""BT-RADS Backend with Ollama LLM Integration"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import csv
import io
import re
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import required LLM modules - these are mandatory
try:
    from llm import get_ollama_client, get_rag_retriever, ALL_PROMPTS
    from utils.text_processing import extract_evidence_with_positions
except ImportError as e:
    print(f"ERROR: Required LLM modules not available: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Check if Ollama is available
try:
    import ollama
    # Test connection to Ollama
    ollama.list()
except Exception as e:
    print(f"ERROR: Cannot connect to Ollama service: {e}")
    print("Please ensure Ollama is installed and running:")
    print("  1. Install Ollama: https://ollama.com/download")
    print("  2. Start Ollama: ollama serve")
    sys.exit(1)

app = FastAPI(title="BT-RADS Backend with LLM")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Patient data storage
patients = []

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
        "service": "BT-RADS Backend"
    }

@app.post("/api/patients/upload")
async def upload_patients(file: UploadFile = File(...)):
    """Upload endpoint that parses CSV and creates patient records"""
    global patients
    
    # Read the file content
    content = await file.read()
    content_str = content.decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(content_str))
    
    # Clear existing mock patients
    patients = []
    
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
            patients.append(patient)
    
    print(f"Received file: {file.filename}")
    print(f"Parsed {len(patients)} patients from CSV")
    
    return patients

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
    patients.append(patient)
    return patient

@app.get("/api/patients")
async def list_patients():
    """List all patients"""
    return patients

@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str):
    """Get a specific patient"""
    for patient in patients:
        if patient["id"] == patient_id:
            return patient
    return {"error": "Patient not found"}

@app.post("/api/patients/{patient_id}/process")
async def start_processing(patient_id: str):
    """Start processing a patient"""
    for patient in patients:
        if patient["id"] == patient_id:
            patient["processing_status"] = "processing"
            return {"message": "Processing started", "patient_id": patient_id}
    return {"error": "Patient not found"}

@app.get("/api/patients/{patient_id}/status")
async def get_status(patient_id: str):
    """Get processing status"""
    for patient in patients:
        if patient["id"] == patient_id:
            return {
                "patient_id": patient_id,
                "status": patient["processing_status"],
                "completed": patient["completed"]
            }
    return {"error": "Patient not found"}


def extract_with_llm(clinical_note: str, extraction_type: str, use_rag: bool = True) -> dict:
    """Extract information using Ollama LLM"""
    if not clinical_note or not clinical_note.strip():
        raise HTTPException(status_code=400, detail="Empty clinical note provided")
    
    try:
        # Get clients
        ollama_client = get_ollama_client()
        rag_retriever = get_rag_retriever()
        
        # Get prompt configuration
        prompt_config = ALL_PROMPTS.get(extraction_type)
        if not prompt_config:
            return None
        
        # Retrieve context with RAG
        query = ""
        if extraction_type == "medications":
            query = "medications steroids dexamethasone avastin bevacizumab treatment"
        elif extraction_type == "radiation_date":
            query = "radiation therapy XRT completed finished date"
        
        context, source_info = rag_retriever.retrieve_with_source_tracking(
            clinical_note, query, use_rag=use_rag
        )
        
        # Extract with LLM
        import time
        start_time = time.time()
        
        result = ollama_client.extract_with_prompt(
            prompt_config=prompt_config,
            context=context,
            temperature=0.0,
            top_k=40,
            top_p=0.95
        )
        
        processing_time = time.time() - start_time
        
        if not result:
            return None
        
        # Parse JSON result
        try:
            if prompt_config.get("output_format") == "json":
                data = json.loads(result)
                # Validate expected fields
                if extraction_type == "medications":
                    if "steroid_status" not in data or "avastin_status" not in data:
                        print(f"Missing expected fields in LLM response: {data}")
                        return None
                elif extraction_type == "radiation_date":
                    if "radiation_date" not in data:
                        print(f"Missing radiation_date in LLM response: {data}")
                        return None
            else:
                data = {"result": result}
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM JSON response: {e}")
            print(f"Raw response: {result}")
            return None
        
        # Extract evidence from context
        evidence = []
        if extraction_type == "medications":
            # Look for medication mentions in retrieved chunks
            for src in source_info[:3]:
                content = src.get("content_preview", "")
                if any(med in content.lower() for med in ["steroid", "dexamethasone", "avastin", "bevacizumab"]):
                    evidence.append({
                        "text": content,
                        "type": "medication",
                        "relevance": src.get("relevance_score", 0.5),
                        "source": "llm_rag",
                        "section": src.get("section", "unknown")
                    })
        elif extraction_type == "radiation_date":
            # Look for date mentions in retrieved chunks
            for src in source_info[:3]:
                content = src.get("content_preview", "")
                if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', content):
                    evidence.append({
                        "text": content,
                        "type": "radiation_date",
                        "relevance": src.get("relevance_score", 0.5),
                        "source": "llm_rag",
                        "section": src.get("section", "unknown")
                    })
        
        # Calculate confidence based on LLM response and evidence
        confidence = 0.8  # Base confidence for successful LLM extraction
        if evidence:
            confidence = min(0.95, confidence + 0.1 * len(evidence))
        
        return {
            "data": data,
            "evidence": evidence,
            "confidence": confidence,
            "processing_time": processing_time,
            "method": "llm",
            "model": ollama_client.default_model,
            "source_tracking": {
                "chunks_analyzed": len(source_info),
                "extraction_method": "llm_with_rag" if use_rag else "llm_full_context",
                "context_length": len(context)
            }
        }
        
    except ImportError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Import error: {e}. Please install dependencies: pip install -r requirements.txt"
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to Ollama: {e}. Please ensure Ollama is running: ollama serve"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM extraction error: {type(e).__name__}: {e}"
        )

@app.post("/api/llm/extract")
async def extract_information(request_data: dict):
    """LLM extraction endpoint using Ollama"""
    clinical_note = request_data.get("clinical_note", "")
    extraction_type = request_data.get("extraction_type", "")
    use_rag = request_data.get("use_rag", True)
    
    if not clinical_note:
        raise HTTPException(status_code=400, detail="Clinical note is required")
    
    if extraction_type not in ["medications", "radiation_date"]:
        raise HTTPException(status_code=400, detail="Invalid extraction type. Must be 'medications' or 'radiation_date'")
    
    # Use LLM extraction
    return extract_with_llm(clinical_note, extraction_type, use_rag)

if __name__ == "__main__":
    print("Starting BT-RADS Backend on http://localhost:5001")
    print("✓ Ollama LLM integration active")
    print("API Documentation available at http://localhost:5001/docs")
    uvicorn.run(app, host="0.0.0.0", port=5001)