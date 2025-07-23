"""Database utilities and initialization"""
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import asyncpg
from contextlib import asynccontextmanager

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/btrads_db")

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"),
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Async database pool
async_pool: Optional[asyncpg.Pool] = None

async def init_db():
    """Initialize database connections and create tables"""
    global async_pool
    
    # Create async connection pool
    if not async_pool:
        async_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=10,
            max_size=20,
            command_timeout=60
        )
    
    # Create tables (for development)
    Base.metadata.create_all(bind=engine)
    
    return async_pool

async def close_db():
    """Close database connections"""
    global async_pool
    if async_pool:
        await async_pool.close()
        async_pool = None

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def get_async_db():
    """Get async database connection"""
    async with async_pool.acquire() as connection:
        yield connection

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