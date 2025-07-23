-- Initialize BT-RADS database schema

-- Create patients table
CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clinical_note TEXT,
    baseline_date DATE,
    followup_date DATE,
    radiation_date DATE,
    baseline_flair_volume FLOAT,
    followup_flair_volume FLOAT,
    flair_change_percentage FLOAT,
    baseline_enhancement_volume FLOAT,
    followup_enhancement_volume FLOAT,
    enhancement_change_percentage FLOAT,
    ground_truth_btrads VARCHAR,
    processing_status VARCHAR DEFAULT 'pending',
    current_node VARCHAR,
    completed BOOLEAN DEFAULT FALSE,
    btrads_result JSONB,
    algorithm_path JSONB,
    validation_history JSONB
);

-- Create agent results table
CREATE TABLE IF NOT EXISTS agent_results (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR,
    agent_id VARCHAR,
    node_id VARCHAR,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extracted_value JSONB,
    confidence FLOAT,
    reasoning TEXT,
    source_highlights JSONB,
    validation_status VARCHAR DEFAULT 'pending',
    validated_value JSONB,
    validator_notes TEXT,
    validated_by VARCHAR,
    validated_at TIMESTAMP,
    processing_time_ms INTEGER,
    llm_model VARCHAR,
    missing_info JSONB
);

-- Create indexes
CREATE INDEX idx_patients_status ON patients(processing_status);
CREATE INDEX idx_agent_results_patient ON agent_results(patient_id);
CREATE INDEX idx_agent_results_node ON agent_results(node_id);
CREATE INDEX idx_agent_results_validation ON agent_results(validation_status);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_patients_updated_at BEFORE UPDATE
    ON patients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();