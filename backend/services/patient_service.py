"""Patient data management service"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
import json
import logging

from sqlalchemy.orm import Session
from sqlalchemy import select

from models.patient import Patient, PatientData
from utils.database import get_async_db, PatientRecord, get_db
from agents.orchestration.agent_orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

class PatientService:
    """Service for managing patient data and processing"""
    
    def __init__(self):
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.orchestrator = None  # Will be initialized with WebSocket manager
    
    def set_orchestrator(self, orchestrator: AgentOrchestrator):
        """Set the agent orchestrator"""
        self.orchestrator = orchestrator
    
    async def create_patient(self, patient_data: PatientData) -> Patient:
        """Create a new patient record"""
        db = next(get_db())
        try:
            # Generate patient ID if not provided
            if not patient_data.patient_id:
                patient_data.patient_id = f"PAT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            patient_record = PatientRecord(
                id=patient_data.patient_id,
                clinical_note=patient_data.clinical_note,
                baseline_date=patient_data.baseline_date,
                followup_date=patient_data.followup_date,
                radiation_date=patient_data.radiation_date,
                baseline_flair_volume=patient_data.baseline_flair_volume,
                followup_flair_volume=patient_data.followup_flair_volume,
                flair_change_percentage=patient_data.flair_change_percentage,
                baseline_enhancement_volume=patient_data.baseline_enhancement_volume,
                followup_enhancement_volume=patient_data.followup_enhancement_volume,
                enhancement_change_percentage=patient_data.enhancement_change_percentage,
                ground_truth_btrads=patient_data.ground_truth_btrads,
                processing_status='pending'
            )
            
            db.add(patient_record)
            db.commit()
            db.refresh(patient_record)
            
            return Patient.from_db_record(patient_record)
        finally:
            db.close()
    
    async def process_csv(self, df: pd.DataFrame) -> List[Patient]:
        """Process uploaded CSV file and create patient records"""
        patients = []
        
        # Expected columns mapping
        column_mapping = {
            'patient_id': ['patient_id', 'id', 'Patient ID', 'pid', 'PID'],
            'clinical_note': ['clinical_note', 'Clinical Note', 'note', 'clinical_note_closest', 'Clinical_Note_Closest'],
            'baseline_date': ['baseline_date', 'Baseline_imaging_date'],
            'followup_date': ['followup_date', 'Followup_imaging_date'],
            'radiation_date': ['radiation_date', 'Radiation_completion_date'],
            'baseline_flair_volume': ['baseline_flair_volume', 'Baseline_flair_volume'],
            'followup_flair_volume': ['followup_flair_volume', 'Followup_flair_volume'],
            'flair_change_percentage': ['flair_change_percentage', 'Volume_Difference_flair_Percentage_Change'],
            'baseline_enhancement_volume': ['baseline_enhancement_volume', 'Baseline_enhancement_volume'],
            'followup_enhancement_volume': ['followup_enhancement_volume', 'Followup_enhancement_volume'],
            'enhancement_change_percentage': ['enhancement_change_percentage', 'Volume_Difference_enhancement_Percentage_Change'],
            'ground_truth_btrads': ['ground_truth_btrads', 'BTRADS (Precise Category)', 'BT-RADS', 'Ground_Truth_BTRADS (Precise Category)', 'Ground_Truth_BTRADS (General Category)']
        }
        
        # Normalize column names
        normalized_df = df.copy()
        for target_col, possible_names in column_mapping.items():
            for col_name in possible_names:
                if col_name in df.columns:
                    normalized_df[target_col] = df[col_name]
                    break
        
        # Process each row
        async with get_async_db() as conn:
            for idx, row in normalized_df.iterrows():
                try:
                    # Create patient data
                    patient_data = PatientData(
                        patient_id=str(row.get('patient_id', f'PT{idx:04d}')),
                        clinical_note=str(row.get('clinical_note', '')),
                        baseline_date=pd.to_datetime(row.get('baseline_date')).date(),
                        followup_date=pd.to_datetime(row.get('followup_date')).date(),
                        radiation_date=pd.to_datetime(row.get('radiation_date')).date() if pd.notna(row.get('radiation_date')) else None,
                        baseline_flair_volume=float(row.get('baseline_flair_volume')) if pd.notna(row.get('baseline_flair_volume')) else None,
                        followup_flair_volume=float(row.get('followup_flair_volume')) if pd.notna(row.get('followup_flair_volume')) else None,
                        flair_change_percentage=float(row.get('flair_change_percentage')) if pd.notna(row.get('flair_change_percentage')) else None,
                        baseline_enhancement_volume=float(row.get('baseline_enhancement_volume')) if pd.notna(row.get('baseline_enhancement_volume')) else None,
                        followup_enhancement_volume=float(row.get('followup_enhancement_volume')) if pd.notna(row.get('followup_enhancement_volume')) else None,
                        enhancement_change_percentage=float(row.get('enhancement_change_percentage')) if pd.notna(row.get('enhancement_change_percentage')) else None,
                        ground_truth_btrads=str(row.get('ground_truth_btrads')) if pd.notna(row.get('ground_truth_btrads')) else None
                    )
                    
                    # Create patient record
                    patient = Patient(
                        id=patient_data.patient_id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        data=patient_data,
                        processing_status="pending",
                        current_node=None,
                        completed=False
                    )
                    
                    # Save to database
                    await self._save_patient(conn, patient)
                    patients.append(patient)
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx}: {str(e)}")
                    continue
        
        logger.info(f"Processed {len(patients)} patients from CSV")
        return patients
    
    async def _save_patient(self, conn, patient: Patient):
        """Save patient to database"""
        query = """
            INSERT INTO patients (
                id, created_at, updated_at, clinical_note,
                baseline_date, followup_date, radiation_date,
                baseline_flair_volume, followup_flair_volume, flair_change_percentage,
                baseline_enhancement_volume, followup_enhancement_volume, enhancement_change_percentage,
                ground_truth_btrads, processing_status, current_node, completed
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            ON CONFLICT (id) DO UPDATE SET
                updated_at = $3,
                clinical_note = $4,
                baseline_date = $5,
                followup_date = $6,
                radiation_date = $7,
                baseline_flair_volume = $8,
                followup_flair_volume = $9,
                flair_change_percentage = $10,
                baseline_enhancement_volume = $11,
                followup_enhancement_volume = $12,
                enhancement_change_percentage = $13,
                ground_truth_btrads = $14
        """
        
        await conn.execute(
            query,
            patient.id,
            patient.created_at,
            patient.updated_at,
            patient.data.clinical_note,
            patient.data.baseline_date,
            patient.data.followup_date,
            patient.data.radiation_date,
            patient.data.baseline_flair_volume,
            patient.data.followup_flair_volume,
            patient.data.flair_change_percentage,
            patient.data.baseline_enhancement_volume,
            patient.data.followup_enhancement_volume,
            patient.data.enhancement_change_percentage,
            patient.data.ground_truth_btrads,
            patient.processing_status,
            patient.current_node,
            patient.completed
        )
    
    async def list_patients(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Patient]:
        """List patients with optional filtering"""
        async with get_async_db() as conn:
            query = "SELECT * FROM patients"
            params = []
            
            if status:
                query += " WHERE processing_status = $1"
                params.append(status)
            
            query += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {skip}"
            
            rows = await conn.fetch(query, *params)
            
            patients = []
            for row in rows:
                patient_data = PatientData(
                    patient_id=row['id'],
                    clinical_note=row['clinical_note'],
                    baseline_date=row['baseline_date'],
                    followup_date=row['followup_date'],
                    radiation_date=row['radiation_date'],
                    baseline_flair_volume=row['baseline_flair_volume'],
                    followup_flair_volume=row['followup_flair_volume'],
                    flair_change_percentage=row['flair_change_percentage'],
                    baseline_enhancement_volume=row['baseline_enhancement_volume'],
                    followup_enhancement_volume=row['followup_enhancement_volume'],
                    enhancement_change_percentage=row['enhancement_change_percentage'],
                    ground_truth_btrads=row['ground_truth_btrads']
                )
                
                patient = Patient(
                    id=row['id'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    data=patient_data,
                    processing_status=row['processing_status'],
                    current_node=row['current_node'],
                    completed=row['completed']
                )
                patients.append(patient)
            
            return patients
    
    async def get_patient(self, patient_id: str) -> Optional[Patient]:
        """Get a specific patient"""
        async with get_async_db() as conn:
            query = "SELECT * FROM patients WHERE id = $1"
            row = await conn.fetchrow(query, patient_id)
            
            if not row:
                return None
            
            patient_data = PatientData(
                patient_id=row['id'],
                clinical_note=row['clinical_note'],
                baseline_date=row['baseline_date'],
                followup_date=row['followup_date'],
                radiation_date=row['radiation_date'],
                baseline_flair_volume=row['baseline_flair_volume'],
                followup_flair_volume=row['followup_flair_volume'],
                flair_change_percentage=row['flair_change_percentage'],
                baseline_enhancement_volume=row['baseline_enhancement_volume'],
                followup_enhancement_volume=row['followup_enhancement_volume'],
                enhancement_change_percentage=row['enhancement_change_percentage'],
                ground_truth_btrads=row['ground_truth_btrads']
            )
            
            return Patient(
                id=row['id'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                data=patient_data,
                processing_status=row['processing_status'],
                current_node=row['current_node'],
                completed=row['completed']
            )
    
    async def start_processing(self, patient_id: str, auto_validate: bool = False):
        """Start processing a patient"""
        if not self.orchestrator:
            raise ValueError("Orchestrator not initialized")
        
        # Get patient data
        patient = await self.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")
        
        # Check if already processing
        if patient_id in self.processing_tasks:
            task = self.processing_tasks[patient_id]
            if not task.done():
                raise ValueError(f"Patient {patient_id} is already being processed")
        
        # Update status
        await self._update_status(patient_id, "processing")
        
        # Start processing task
        task = asyncio.create_task(
            self.orchestrator.process_patient(patient.data, auto_validate)
        )
        self.processing_tasks[patient_id] = task
        
        # Handle completion
        task.add_done_callback(
            lambda t: asyncio.create_task(self._handle_completion(patient_id, t))
        )
    
    async def _handle_completion(self, patient_id: str, task: asyncio.Task):
        """Handle processing completion"""
        try:
            result = task.result()
            
            # Update database with results
            async with get_async_db() as conn:
                query = """
                    UPDATE patients 
                    SET processing_status = 'completed',
                        completed = true,
                        btrads_result = $2,
                        algorithm_path = $3,
                        updated_at = $4
                    WHERE id = $1
                """
                
                await conn.execute(
                    query,
                    patient_id,
                    json.dumps(result.dict()),
                    json.dumps(result.algorithm_path.dict()),
                    datetime.utcnow()
                )
            
        except Exception as e:
            logger.error(f"Processing failed for patient {patient_id}: {str(e)}")
            await self._update_status(patient_id, "error")
        
        finally:
            # Remove from active tasks
            self.processing_tasks.pop(patient_id, None)
    
    async def _update_status(self, patient_id: str, status: str, current_node: Optional[str] = None):
        """Update patient processing status"""
        async with get_async_db() as conn:
            query = "UPDATE patients SET processing_status = $2, current_node = $3, updated_at = $4 WHERE id = $1"
            await conn.execute(query, patient_id, status, current_node, datetime.utcnow())
    
    async def get_processing_status(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get current processing status"""
        patient = await self.get_patient(patient_id)
        if not patient:
            return None
        
        status = {
            "patient_id": patient_id,
            "status": patient.processing_status,
            "current_node": patient.current_node,
            "completed": patient.completed,
            "is_processing": patient_id in self.processing_tasks and not self.processing_tasks[patient_id].done()
        }
        
        # Add result if completed
        if patient.completed:
            async with get_async_db() as conn:
                query = "SELECT btrads_result FROM patients WHERE id = $1"
                row = await conn.fetchrow(query, patient_id)
                if row and row['btrads_result']:
                    status['result'] = row['btrads_result']
        
        return status