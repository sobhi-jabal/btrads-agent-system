"""BT-RADS flowchart configuration and logic"""
from typing import Dict, Any, Optional

class BTRADSFlowchart:
    """BT-RADS flowchart structure and navigation"""
    
    def __init__(self):
        self.nodes = self._build_flowchart()
    
    def _build_flowchart(self) -> Dict[str, Dict[str, Any]]:
        """Build the BT-RADS flowchart structure"""
        return {
            # Node 1: Suitable Prior Assessment
            "node_1_suitable_prior": {
                "id": "node_1_suitable_prior",
                "type": "data_extraction",
                "agent": "prior_assessment",
                "label": "Suitable Prior?",
                "description": "Determine if suitable prior imaging is available",
                "next_nodes": {
                    "yes": "node_2_imaging_assessment",
                    "no": "outcome_bt_0",
                    "unknown": "node_2_imaging_assessment"  # Fallback: assume prior available
                },
                "default_next": "node_2_imaging_assessment"
            },
            
            # Outcome: BT-0
            "outcome_bt_0": {
                "id": "outcome_bt_0",
                "type": "outcome",
                "btrads_score": "0",
                "label": "BT-0 (Baseline)",
                "description": "No suitable prior for comparison"
            },
            
            # Node 2: Imaging Assessment
            "node_2_imaging_assessment": {
                "id": "node_2_imaging_assessment",
                "type": "data_extraction",
                "agent": "imaging_comparison",
                "label": "Imaging Assessment",
                "description": "Compare current with prior imaging",
                "next_nodes": {
                    "improved": "node_3a_medications",
                    "unchanged": "outcome_bt_2",
                    "worse": "node_4_time_since_xrt",
                    "unknown": "outcome_bt_2"  # Fallback: assume stable
                },
                "default_next": "outcome_bt_2"
            },
            
            # Outcome: BT-2
            "outcome_bt_2": {
                "id": "outcome_bt_2",
                "type": "outcome",
                "btrads_score": "2",
                "label": "BT-2 (Stable)",
                "description": "No significant change"
            },
            
            # Node 3A: Medication Effects
            "node_3a_medications": {
                "id": "node_3a_medications",
                "type": "data_extraction",
                "agent": "medication_effects",
                "label": "On Medications?",
                "description": "Check for Avastin or increasing steroids",
                "next_nodes": {
                    "avastin": "node_3b_avastin_response",
                    "increasing_steroids": "node_3c_steroid_effects",
                    "neither": "outcome_bt_1a",
                    "unknown": "outcome_bt_1a"  # Fallback: assume no medication effect
                },
                "default_next": "outcome_bt_1a"
            },
            
            # Node 3B: Avastin Response
            "node_3b_avastin_response": {
                "id": "node_3b_avastin_response",
                "type": "data_extraction",
                "agent": "avastin_response",
                "label": "Avastin Response Type",
                "description": "Determine type of Avastin response",
                "next_nodes": {
                    "first_study_enh_only": "outcome_bt_1b",
                    "sustained_improvement": "outcome_bt_1a",
                    "unknown": "outcome_bt_1b"  # Fallback: conservative
                },
                "default_next": "outcome_bt_1b"
            },
            
            # Node 3C: Steroid Effects
            "node_3c_steroid_effects": {
                "id": "node_3c_steroid_effects",
                "type": "data_extraction",
                "agent": "steroid_effects",
                "label": "Steroid Effect Likely?",
                "description": "Determine if steroids explain improvement",
                "next_nodes": {
                    "likely_steroid_effect": "outcome_bt_1b",
                    "unlikely_steroid_effect": "outcome_bt_1a",
                    "unknown": "outcome_bt_1b"  # Fallback: conservative
                },
                "default_next": "outcome_bt_1b"
            },
            
            # Outcomes: BT-1a and BT-1b
            "outcome_bt_1a": {
                "id": "outcome_bt_1a",
                "type": "outcome",
                "btrads_score": "1a",
                "label": "BT-1a (Improved)",
                "description": "True improvement"
            },
            
            "outcome_bt_1b": {
                "id": "outcome_bt_1b",
                "type": "outcome",
                "btrads_score": "1b",
                "label": "BT-1b (Medication Effect)",
                "description": "Improvement due to medication"
            },
            
            # Node 4: Time Since XRT
            "node_4_time_since_xrt": {
                "id": "node_4_time_since_xrt",
                "type": "data_extraction",
                "agent": "radiation_timeline",
                "label": "Time Since XRT",
                "description": "Check if within 90 days of radiation",
                "next_nodes": {
                    "within_90_days": "outcome_bt_3a",
                    "beyond_90_days": "node_5_what_is_worse",
                    "unknown": "node_5_what_is_worse"  # Fallback: assume >90 days
                },
                "default_next": "node_5_what_is_worse"
            },
            
            # Outcome: BT-3a
            "outcome_bt_3a": {
                "id": "outcome_bt_3a",
                "type": "outcome",
                "btrads_score": "3a",
                "label": "BT-3a (Favor Treatment)",
                "description": "Worsening within 90 days of XRT"
            },
            
            # Node 5: What is Worse
            "node_5_what_is_worse": {
                "id": "node_5_what_is_worse",
                "type": "data_extraction",
                "agent": "component_analysis",
                "label": "What is Worse?",
                "description": "Determine which components are worse",
                "next_nodes": {
                    "flair_or_enh": "outcome_bt_3b",
                    "flair_and_enh": "node_6_how_much_worse",
                    "unknown": "outcome_bt_3b"  # Fallback: conservative
                },
                "default_next": "outcome_bt_3b"
            },
            
            # Outcome: BT-3b
            "outcome_bt_3b": {
                "id": "outcome_bt_3b",
                "type": "outcome",
                "btrads_score": "3b",
                "label": "BT-3b (Indeterminate)",
                "description": "Mixed or uncertain worsening"
            },
            
            # Node 6: How Much Worse
            "node_6_how_much_worse": {
                "id": "node_6_how_much_worse",
                "type": "data_extraction",
                "agent": "extent_analysis",
                "label": "How Much Worse?",
                "description": "Apply 40% threshold rule",
                "next_nodes": {
                    "major": "outcome_bt_4",
                    "minor": "node_7_progressive",
                    "unknown": "outcome_bt_3c"  # Fallback: conservative
                },
                "default_next": "outcome_bt_3c"
            },
            
            # Node 7: Progressive Pattern
            "node_7_progressive": {
                "id": "node_7_progressive",
                "type": "data_extraction",
                "agent": "progression_pattern",
                "label": "Progressive?",
                "description": "Check for progression over multiple studies",
                "next_nodes": {
                    "yes": "outcome_bt_4",
                    "no": "outcome_bt_3c",
                    "unknown": "outcome_bt_3c"  # Fallback: conservative
                },
                "default_next": "outcome_bt_3c"
            },
            
            # Outcomes: BT-3c and BT-4
            "outcome_bt_3c": {
                "id": "outcome_bt_3c",
                "type": "outcome",
                "btrads_score": "3c",
                "label": "BT-3c (Favor Tumor)",
                "description": "Worsening favoring tumor"
            },
            
            "outcome_bt_4": {
                "id": "outcome_bt_4",
                "type": "outcome",
                "btrads_score": "4",
                "label": "BT-4 (Highly Suspicious)",
                "description": "Highly suspicious for tumor progression"
            }
        }
    
    def get_node(self, node_id: str) -> Dict[str, Any]:
        """Get a specific node configuration"""
        if node_id not in self.nodes:
            raise ValueError(f"Unknown node: {node_id}")
        return self.nodes[node_id]
    
    def get_next_node(self, current_node_id: str, decision: str) -> str:
        """Get the next node based on current node and decision"""
        node = self.get_node(current_node_id)
        
        if node["type"] == "outcome":
            return None  # Terminal node
        
        next_nodes = node.get("next_nodes", {})
        return next_nodes.get(decision, node.get("default_next"))
    
    def is_terminal(self, node_id: str) -> bool:
        """Check if a node is terminal (outcome)"""
        node = self.get_node(node_id)
        return node["type"] == "outcome"
    
    def get_all_nodes(self) -> Dict[str, Dict[str, Any]]:
        """Get all nodes in the flowchart"""
        return self.nodes.copy()