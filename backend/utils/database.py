"""Database utilities and initialization"""
import os
import pandas as pd
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager
from datetime import datetime
import json

# Database configuration - Using SQLite for simple local deployment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./btrads.db")

# SQLAlchemy setup
if "sqlite" in DATABASE_URL:
    # SQLite configuration for local deployment
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL configuration (for production if needed)
    engine = create_engine(
        DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"),
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# For SQLite, we don't need async pool
async_pool = None

async def init_db():
    """Initialize database and create tables"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Load sample data if database is empty
    db = SessionLocal()
    try:
        # Check if we have any patients
        patient_count = db.query(PatientRecord).count()
        
        if patient_count == 0:
            print("Database is empty. NOT loading sample data to keep clean state.")
            # DISABLED - We don't want sample data on startup
            # load_sample_data(db)
            # print("Sample data loaded successfully!")
    finally:
        db.close()
    
    return None

async def close_db():
    """Close database connections"""
    # For SQLite, we don't need to close a pool
    pass

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def get_async_db():
    """Get database connection (using sync for SQLite)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database models
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Float, Date, Integer, Text
from datetime import datetime

class PatientRecord(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Patient data
    clinical_note = Column(Text)
    baseline_date = Column(Date)
    followup_date = Column(Date)
    radiation_date = Column(Date, nullable=True)
    
    # Volume measurements
    baseline_flair_volume = Column(Float, nullable=True)
    followup_flair_volume = Column(Float, nullable=True)
    flair_change_percentage = Column(Float, nullable=True)
    baseline_enhancement_volume = Column(Float, nullable=True)
    followup_enhancement_volume = Column(Float, nullable=True)
    enhancement_change_percentage = Column(Float, nullable=True)
    
    # Ground truth
    ground_truth_btrads = Column(String, nullable=True)
    
    # Processing status
    processing_status = Column(String, default="pending")
    current_node = Column(String, nullable=True)
    completed = Column(Boolean, default=False)
    
    # Results
    btrads_result = Column(JSON, nullable=True)
    algorithm_path = Column(JSON, nullable=True)
    validation_history = Column(JSON, nullable=True)
    validation_result = Column(JSON, nullable=True)
    user_corrections = Column(JSON, nullable=True)

class AgentResultRecord(Base):
    __tablename__ = "agent_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, index=True)
    agent_id = Column(String)
    node_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Extraction results
    extracted_value = Column(JSON)
    confidence = Column(Float)
    reasoning = Column(Text)
    source_highlights = Column(JSON)
    
    # Validation
    validation_status = Column(String, default="pending")
    validated_value = Column(JSON, nullable=True)
    validator_notes = Column(Text, nullable=True)
    validated_by = Column(String, nullable=True)
    validated_at = Column(DateTime, nullable=True)
    
    # Metadata
    processing_time_ms = Column(Integer)
    llm_model = Column(String)
    missing_info = Column(JSON, nullable=True)
    extra_metadata = Column(JSON, nullable=True)


def load_sample_data(db: Session):
    """Load sample data from CSV file"""
    import os
    
    # Try to find the CSV file
    csv_paths = [
        "./sample_btrads_data.csv",
        "../sample_btrads_data.csv",
        "../../sample_btrads_data.csv",
        "/Users/sobhi/Desktop/Claude_Code/Duke/Evan/BTRADS_Agents/btrads-agent-system/sample_btrads_data.csv"
    ]
    
    csv_file = None
    for path in csv_paths:
        if os.path.exists(path):
            csv_file = path
            break
    
    if not csv_file:
        print("Warning: No sample data file found")
        return
    
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
    # Map CSV columns to database fields
    for _, row in df.iterrows():
        patient = PatientRecord(
            id=row['Patient ID'],
            clinical_note=row['Clinical Note'],
            baseline_date=pd.to_datetime(row['Baseline_imaging_date']).date() if pd.notna(row['Baseline_imaging_date']) else None,
            followup_date=pd.to_datetime(row['Followup_imaging_date']).date() if pd.notna(row['Followup_imaging_date']) else None,
            radiation_date=pd.to_datetime(row['Radiation_completion_date']).date() if pd.notna(row['Radiation_completion_date']) else None,
            baseline_flair_volume=float(row['Baseline_flair_volume']) if pd.notna(row['Baseline_flair_volume']) else None,
            followup_flair_volume=float(row['Followup_flair_volume']) if pd.notna(row['Followup_flair_volume']) else None,
            flair_change_percentage=float(row['Volume_Difference_flair_Percentage_Change']) if pd.notna(row['Volume_Difference_flair_Percentage_Change']) else None,
            baseline_enhancement_volume=float(row['Baseline_enhancement_volume']) if pd.notna(row['Baseline_enhancement_volume']) else None,
            followup_enhancement_volume=float(row['Followup_enhancement_volume']) if pd.notna(row['Followup_enhancement_volume']) else None,
            enhancement_change_percentage=float(row['Volume_Difference_enhancement_Percentage_Change']) if pd.notna(row['Volume_Difference_enhancement_Percentage_Change']) else None,
            ground_truth_btrads=row['BTRADS (Precise Category)'] if pd.notna(row['BTRADS (Precise Category)']) else None,
            processing_status='pending',
            completed=False
        )
        db.add(patient)
    
    db.commit()
    print(f"Loaded {len(df)} patients from {csv_file}")