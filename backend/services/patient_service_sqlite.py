"""Patient service with SQLite support"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import logging

from models.patient import Patient, PatientData, ProcessingStatus
from utils.database import get_async_db, PatientRecord

logger = logging.getLogger(__name__)


class PatientService:
    """Service for managing patient data using SQLite"""
    
    def __init__(self):
        self.orchestrator = None
        self.processing_tasks = {}
        
    def set_orchestrator(self, orchestrator):
        """Set the orchestrator instance"""
        self.orchestrator = orchestrator
    
    async def list_patients(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Patient]:
        """List patients with optional filtering"""
        async with get_async_db() as db:
            # Build query using SQLAlchemy
            query = db.query(PatientRecord)
            
            if status:
                query = query.filter(PatientRecord.processing_status == status)
            
            query = query.order_by(PatientRecord.created_at.desc())
            query = query.offset(skip).limit(limit)
            
            records = query.all()
            
            patients = []
            for record in records:
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
                
                # Parse JSON fields
                btrads_result = json.loads(record.btrads_result) if record.btrads_result else None
                validation_result = json.loads(record.validation_result) if record.validation_result else None
                user_corrections = json.loads(record.user_corrections) if record.user_corrections else None
                
                patient = Patient(
                    id=record.id,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    data=patient_data,
                    processing_status=record.processing_status,
                    current_node=record.current_node,
                    completed=record.completed,
                    btrads_result=btrads_result,
                    validation_result=validation_result,
                    user_corrections=user_corrections
                )
                patients.append(patient)
            
            return patients
    
    async def get_patient(self, patient_id: str) -> Optional[Patient]:
        """Get a specific patient"""
        async with get_async_db() as db:
            record = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
            
            if not record:
                return None
            
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
            
            # Parse JSON fields
            btrads_result = json.loads(record.btrads_result) if record.btrads_result else None
            validation_result = json.loads(record.validation_result) if record.validation_result else None
            user_corrections = json.loads(record.user_corrections) if record.user_corrections else None
            
            return Patient(
                id=record.id,
                created_at=record.created_at,
                updated_at=record.updated_at,
                data=patient_data,
                processing_status=record.processing_status,
                current_node=record.current_node,
                completed=record.completed,
                btrads_result=btrads_result,
                validation_result=validation_result,
                user_corrections=user_corrections
            )
    
    async def create_patient(self, patient_data: PatientData) -> Patient:
        """Create a new patient"""
        async with get_async_db() as db:
            # Generate ID if not provided
            patient_id = patient_data.patient_id
            if not patient_id:
                import uuid
                patient_id = f"PT-{str(uuid.uuid4())[:8]}"
            
            record = PatientRecord(
                id=patient_id,
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
                processing_status='pending',
                completed=False
            )
            
            db.add(record)
            db.commit()
            db.refresh(record)
            
            return Patient(
                id=record.id,
                created_at=record.created_at,
                updated_at=record.updated_at,
                data=patient_data,
                processing_status=record.processing_status,
                current_node=record.current_node,
                completed=record.completed
            )
    
    async def update_patient_status(
        self,
        patient_id: str,
        status: str,
        current_node: Optional[str] = None,
        btrads_result: Optional[Dict[str, Any]] = None
    ) -> Optional[Patient]:
        """Update patient processing status"""
        async with get_async_db() as db:
            record = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
            
            if not record:
                return None
            
            record.processing_status = status
            record.updated_at = datetime.utcnow()
            
            if current_node:
                record.current_node = current_node
            
            if btrads_result:
                record.btrads_result = json.dumps(btrads_result)
                
            if status == 'completed':
                record.completed = True
            
            db.commit()
            db.refresh(record)
            
            return await self.get_patient(patient_id)
    
    async def save_validation_result(
        self,
        patient_id: str,
        validation_result: Dict[str, Any]
    ) -> Optional[Patient]:
        """Save validation result for a patient"""
        async with get_async_db() as db:
            record = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
            
            if not record:
                return None
            
            record.validation_result = json.dumps(validation_result)
            record.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(record)
            
            return await self.get_patient(patient_id)
    
    async def save_user_corrections(
        self,
        patient_id: str,
        corrections: Dict[str, Any]
    ) -> Optional[Patient]:
        """Save user corrections for a patient"""
        async with get_async_db() as db:
            record = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
            
            if not record:
                return None
            
            record.user_corrections = json.dumps(corrections)
            record.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(record)
            
            return await self.get_patient(patient_id)
    
    async def process_csv(self, df) -> List[Patient]:
        """Process uploaded CSV file and create patient records"""
        import pandas as pd
        
        patients = []
        errors = []
        
        # Log what columns we received
        logger.info(f"CSV columns received: {list(df.columns)}")
        logger.info(f"Number of rows: {len(df)}")
        
        # Expected columns mapping - updated to include your CSV format
        column_mapping = {
            'patient_id': ['pid', 'PID', 'patient_id', 'id', 'Patient ID'],
            'clinical_note': ['clinical_note_closest', 'Clinical_Note_Closest', 'clinical_note', 'Clinical Note', 'note'],
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
        found_mappings = {}
        for target_col, possible_names in column_mapping.items():
            column_found = False
            for col_name in possible_names:
                if col_name in df.columns:
                    normalized_df[target_col] = df[col_name]
                    found_mappings[target_col] = col_name
                    column_found = True
                    break
            if not column_found and target_col in ['patient_id', 'clinical_note']:
                # These are required fields
                logger.warning(f"Required column '{target_col}' not found. Looked for: {possible_names}")
        
        logger.info(f"Column mappings found: {found_mappings}")
        
        # Process each row
        for idx, row in normalized_df.iterrows():
            try:
                # Generate unique patient ID
                import uuid
                base_id = str(row.get('patient_id', f'PT{idx:04d}'))
                # Always append a unique suffix to avoid duplicates
                unique_id = f"{base_id}_{str(uuid.uuid4())[:8]}"
                
                # Create patient data - only include fields that are present
                patient_data_dict = {
                    'patient_id': unique_id,
                    'clinical_note': str(row.get('clinical_note', ''))
                }
                
                # Add optional date fields only if they exist and are not null
                if 'baseline_date' in row and pd.notna(row.get('baseline_date')):
                    patient_data_dict['baseline_date'] = pd.to_datetime(row.get('baseline_date')).date()
                if 'followup_date' in row and pd.notna(row.get('followup_date')):
                    patient_data_dict['followup_date'] = pd.to_datetime(row.get('followup_date')).date()
                if 'radiation_date' in row and pd.notna(row.get('radiation_date')):
                    patient_data_dict['radiation_date'] = pd.to_datetime(row.get('radiation_date')).date()
                
                # Add optional volume fields only if they exist and are not null
                if 'baseline_flair_volume' in row and pd.notna(row.get('baseline_flair_volume')):
                    patient_data_dict['baseline_flair_volume'] = float(row.get('baseline_flair_volume'))
                if 'followup_flair_volume' in row and pd.notna(row.get('followup_flair_volume')):
                    patient_data_dict['followup_flair_volume'] = float(row.get('followup_flair_volume'))
                if 'flair_change_percentage' in row and pd.notna(row.get('flair_change_percentage')):
                    patient_data_dict['flair_change_percentage'] = float(row.get('flair_change_percentage'))
                if 'baseline_enhancement_volume' in row and pd.notna(row.get('baseline_enhancement_volume')):
                    patient_data_dict['baseline_enhancement_volume'] = float(row.get('baseline_enhancement_volume'))
                if 'followup_enhancement_volume' in row and pd.notna(row.get('followup_enhancement_volume')):
                    patient_data_dict['followup_enhancement_volume'] = float(row.get('followup_enhancement_volume'))
                if 'enhancement_change_percentage' in row and pd.notna(row.get('enhancement_change_percentage')):
                    patient_data_dict['enhancement_change_percentage'] = float(row.get('enhancement_change_percentage'))
                if 'ground_truth_btrads' in row and pd.notna(row.get('ground_truth_btrads')):
                    patient_data_dict['ground_truth_btrads'] = str(row.get('ground_truth_btrads'))
                
                patient_data = PatientData(**patient_data_dict)
                
                # Save patient using existing create_patient method
                patient = await self.create_patient(patient_data)
                patients.append(patient)
                logger.info(f"Successfully created patient: {patient.id}")
                
            except Exception as e:
                error_msg = f"Error processing row {idx}: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Row data: {row.to_dict()}")
                logger.error(f"Available columns in normalized_df: {list(normalized_df.columns)}")
                errors.append(error_msg)
                continue
        
        # Report results
        logger.info(f"Processed {len(patients)} patients from CSV")
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during processing")
            for error in errors[:5]:  # Log first 5 errors
                logger.warning(error)
        
        # If no patients were created and we had errors, raise an exception
        if not patients and errors:
            error_summary = f"Failed to process any patients. First error: {errors[0] if errors else 'Unknown error'}"
            logger.error(error_summary)
            # Still return empty list instead of raising, but log the issue
            # This allows the frontend to see the empty result
        
        return patients
    
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
            async with get_async_db() as db:
                db_patient = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
                if db_patient and db_patient.btrads_result:
                    status['result'] = db_patient.btrads_result
        
        return status
    
    async def start_processing(self, patient_id: str, auto_validate: bool = False) -> Dict[str, Any]:
        """Start processing a patient through the BT-RADS workflow"""
        import asyncio
        
        # Check if already processing
        if patient_id in self.processing_tasks and not self.processing_tasks[patient_id].done():
            return {"status": "already_processing"}
        
        # Start processing in background
        task = asyncio.create_task(self.process_patient(patient_id))
        self.processing_tasks[patient_id] = task
        
        return {"status": "processing_started", "patient_id": patient_id}
    
    async def process_patient(self, patient_id: str) -> Dict[str, Any]:
        """Process a patient through the BT-RADS workflow"""
        if not self.orchestrator:
            raise ValueError("Orchestrator not set")
        
        # Get patient data
        patient = await self.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")
        
        # Update status to processing
        await self.update_patient_status(patient_id, ProcessingStatus.PROCESSING)
        
        try:
            # Add patient_id to the data if not present
            if patient.data and not hasattr(patient.data, 'patient_id'):
                patient.data.patient_id = patient.id
            
            # Run the orchestration
            result = await self.orchestrator.process_patient(patient.data)
            
            # Convert BTRADSResult to dict for storage and response
            # Use mode='json' to handle datetime serialization
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump(mode='json')
            else:
                # Fallback for older Pydantic versions
                import json
                result_dict = json.loads(result.json())
            
            # Extract the final node from the algorithm path
            final_node = None
            if hasattr(result, 'algorithm_path') and result.algorithm_path:
                # Get the last node from the path
                if hasattr(result.algorithm_path, 'nodes') and result.algorithm_path.nodes:
                    final_node = result.algorithm_path.nodes[-1].get('node_id') if result.algorithm_path.nodes else None
            
            # Update with results
            await self.update_patient_status(
                patient_id,
                ProcessingStatus.COMPLETED,
                current_node=final_node,
                btrads_result=result_dict
            )
            
            return result_dict
            
        except Exception as e:
            logger.error(f"Error processing patient {patient_id}: {e}")
            await self.update_patient_status(
                patient_id,
                ProcessingStatus.ERROR,
                btrads_result={"error": str(e)}
            )
            raise