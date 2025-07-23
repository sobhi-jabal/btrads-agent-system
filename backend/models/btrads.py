"""BT-RADS specific models"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

class BTRADSScore(str, Enum):
    """BT-RADS classification scores"""
    BT_0 = "0"      # Baseline
    BT_1A = "1a"    # Improved
    BT_1B = "1b"    # Improved (medication effect)
    BT_2 = "2"      # Stable
    BT_3A = "3a"    # Worse (favor treatment)
    BT_3B = "3b"    # Worse (indeterminate)
    BT_3C = "3c"    # Worse (favor tumor)
    BT_4 = "4"      # Highly suspicious

class NodeType(str, Enum):
    """Types of nodes in the BT-RADS flowchart"""
    DECISION = "decision"
    OUTCOME = "outcome"
    DATA_EXTRACTION = "data_extraction"

class BTRADSNode(BaseModel):
    """Node in the BT-RADS decision tree"""
    id: str
    type: NodeType
    label: str
    description: str
    
    # For decision nodes
    question: Optional[str] = None
    options: Optional[Dict[str, str]] = None  # value -> next_node_id
    
    # For data extraction nodes
    extraction_type: Optional[str] = None
    required_data: Optional[List[str]] = None
    
    # For outcome nodes
    btrads_score: Optional[BTRADSScore] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "node_1_suitable_prior",
                "type": "decision",
                "label": "Suitable Prior?",
                "description": "Determine if suitable prior imaging is available",
                "question": "Is there a suitable prior study for comparison?",
                "options": {
                    "yes": "node_2_imaging_assessment",
                    "no": "outcome_bt_0"
                }
            }
        }

class BTRADSPath(BaseModel):
    """Path taken through the BT-RADS flowchart"""
    patient_id: str
    nodes_visited: List[str] = []
    decisions_made: Dict[str, Any] = {}
    final_score: Optional[BTRADSScore] = None
    completed: bool = False
    
    def add_node(self, node_id: str, decision: Optional[Any] = None):
        """Add a node to the path"""
        self.nodes_visited.append(node_id)
        if decision is not None:
            self.decisions_made[node_id] = decision

class BTRADSResult(BaseModel):
    """Final BT-RADS assessment result"""
    patient_id: str
    score: BTRADSScore
    reasoning: str
    algorithm_path: BTRADSPath
    
    # Supporting data
    volume_assessment: Optional[str] = None
    medication_effects: Optional[str] = None
    time_since_radiation: Optional[int] = None
    
    # Validation tracking
    total_validations: int = 0
    modifications_made: int = 0
    confidence_score: float = Field(ge=0, le=1)
    
    # Timestamps
    started_at: datetime
    completed_at: datetime
    processing_duration_seconds: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "PT001",
                "score": "1a",
                "reasoning": "Imaging shows improvement without medication effects",
                "confidence_score": 0.92,
                "total_validations": 5,
                "modifications_made": 1
            }
        }