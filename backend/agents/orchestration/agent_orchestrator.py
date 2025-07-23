"""Agent orchestrator for managing BT-RADS flowchart execution"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.extraction.prior_assessment import PriorAssessmentAgent
from agents.extraction.imaging_comparison import ImagingComparisonAgent
from agents.extraction.medication_status import MedicationStatusAgent
from agents.extraction.radiation_timeline import RadiationTimelineAgent
from agents.extraction.component_analysis import ComponentAnalysisAgent
from agents.extraction.extent_analysis import ExtentAnalysisAgent
from agents.extraction.progression_pattern import ProgressionPatternAgent

from models.patient import PatientData
from models.agent import AgentResult, ValidationStatus
from models.btrads import BTRADSPath, BTRADSResult, BTRADSScore
from services.websocket_manager import WebSocketManager
from utils.flowchart import BTRADSFlowchart

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Orchestrates agent execution through BT-RADS flowchart"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.flowchart = BTRADSFlowchart()
        
        # Initialize agents
        self.agents = {
            "prior_assessment": PriorAssessmentAgent(),
            "imaging_comparison": ImagingComparisonAgent(),
            "medication_status": MedicationStatusAgent(),
            "radiation_timeline": RadiationTimelineAgent(),
            "component_analysis": ComponentAnalysisAgent(),
            "extent_analysis": ExtentAnalysisAgent(),
            "progression_pattern": ProgressionPatternAgent(),
        }
        
        # Processing state
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def process_patient(
        self,
        patient_data: PatientData,
        auto_validate: bool = False
    ) -> BTRADSResult:
        """Process a patient through the BT-RADS flowchart"""
        patient_id = patient_data.patient_id
        start_time = datetime.utcnow()
        
        # Initialize session
        self.active_sessions[patient_id] = {
            "data": patient_data,
            "path": BTRADSPath(patient_id=patient_id),
            "results": {},
            "context": self._prepare_context(patient_data),
            "auto_validate": auto_validate
        }
        
        try:
            # Start at the root node
            await self._notify_status(patient_id, "started", {"node": "root"})
            
            # Process through flowchart
            final_score = await self._process_node(
                patient_id,
                "node_1_suitable_prior"
            )
            
            # Create final result
            session = self.active_sessions[patient_id]
            result = BTRADSResult(
                patient_id=patient_id,
                score=final_score,
                reasoning=self._generate_reasoning(session),
                algorithm_path=session["path"],
                volume_assessment=session["results"].get("imaging_comparison", {}).get("extracted_value"),
                medication_effects=session["results"].get("medication_status", {}).get("extracted_value"),
                time_since_radiation=session["context"].get("days_since_radiation"),
                total_validations=len([r for r in session["results"].values() if r.get("validated")]),
                modifications_made=len([r for r in session["results"].values() if r.get("modified")]),
                confidence_score=self._calculate_confidence(session),
                started_at=start_time,
                completed_at=datetime.utcnow(),
                processing_duration_seconds=(datetime.utcnow() - start_time).total_seconds()
            )
            
            await self._notify_status(patient_id, "completed", {"result": result.dict()})
            return result
            
        except Exception as e:
            logger.error(f"Error processing patient {patient_id}: {str(e)}")
            await self._notify_status(patient_id, "error", {"error": str(e)})
            raise
        finally:
            # Clean up session
            self.active_sessions.pop(patient_id, None)
    
    async def _process_node(
        self,
        patient_id: str,
        node_id: str
    ) -> BTRADSScore:
        """Process a single node in the flowchart"""
        session = self.active_sessions[patient_id]
        path = session["path"]
        
        # Add node to path
        path.add_node(node_id)
        
        # Notify UI of node activation
        await self._notify_status(patient_id, "node_activated", {
            "node_id": node_id,
            "from_node": path.nodes_visited[-2] if len(path.nodes_visited) > 1 else None
        })
        
        # Get node configuration
        node = self.flowchart.get_node(node_id)
        
        # Handle different node types
        if node["type"] == "outcome":
            # Terminal node - return BT-RADS score
            return BTRADSScore(node["btrads_score"])
        
        elif node["type"] == "data_extraction":
            # Run appropriate agent
            agent_result = await self._run_agent(patient_id, node)
            
            # Wait for validation if needed
            if not session["auto_validate"]:
                validated_value = await self._wait_for_validation(
                    patient_id,
                    node_id,
                    agent_result
                )
            else:
                validated_value = agent_result.extracted_value
            
            # Store result
            session["results"][node["agent"]] = {
                "result": agent_result,
                "validated": not session["auto_validate"],
                "validated_value": validated_value,
                "modified": validated_value != agent_result.extracted_value
            }
            
            # Determine next node based on value
            next_node = self._determine_next_node(node, validated_value)
            path.add_node(node_id, validated_value)
            
        elif node["type"] == "decision":
            # Decision node - determine path based on context
            decision = self._make_decision(node, session)
            next_node = node["options"][decision]
            path.add_node(node_id, decision)
        
        # Continue to next node
        return await self._process_node(patient_id, next_node)
    
    async def _run_agent(
        self,
        patient_id: str,
        node: Dict[str, Any]
    ) -> AgentResult:
        """Run the appropriate agent for a node"""
        session = self.active_sessions[patient_id]
        agent_name = node["agent"]
        
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        agent = self.agents[agent_name]
        
        # Notify UI of agent start
        await self._notify_status(patient_id, "agent_started", {
            "node_id": node["id"],
            "agent": agent_name
        })
        
        # Run agent
        result = await agent.extract(
            clinical_note=session["data"].clinical_note,
            context=session["context"],
            patient_id=patient_id
        )
        
        # Notify UI of completion
        await self._notify_status(patient_id, "extraction_complete", {
            "node_id": node["id"],
            "agent": agent_name,
            "data": result.dict(),
            "requires_validation": not session["auto_validate"]
        })
        
        return result
    
    async def _wait_for_validation(
        self,
        patient_id: str,
        node_id: str,
        agent_result: AgentResult
    ) -> Any:
        """Wait for clinician validation"""
        # Create validation request
        validation_id = f"{patient_id}_{node_id}_{agent_result.timestamp.timestamp()}"
        
        # Store pending validation
        session = self.active_sessions[patient_id]
        session["pending_validation"] = {
            "id": validation_id,
            "node_id": node_id,
            "result": agent_result,
            "event": asyncio.Event()
        }
        
        # Notify UI
        await self._notify_status(patient_id, "validation_required", {
            "validation_id": validation_id,
            "node_id": node_id,
            "agent_result": agent_result.dict()
        })
        
        # Wait for validation
        await session["pending_validation"]["event"].wait()
        
        # Return validated value
        return session["pending_validation"]["validated_value"]
    
    async def validate_result(
        self,
        patient_id: str,
        validation_id: str,
        validated_value: Any,
        notes: Optional[str] = None
    ):
        """Handle validation from clinician"""
        session = self.active_sessions.get(patient_id)
        if not session or "pending_validation" not in session:
            raise ValueError("No pending validation found")
        
        pending = session["pending_validation"]
        if pending["id"] != validation_id:
            raise ValueError("Validation ID mismatch")
        
        # Store validated value
        pending["validated_value"] = validated_value
        pending["notes"] = notes
        
        # Notify waiting coroutine
        pending["event"].set()
        
        # Notify UI
        await self._notify_status(patient_id, "validation_complete", {
            "validation_id": validation_id,
            "validated_value": validated_value
        })
    
    def _prepare_context(self, patient_data: PatientData) -> Dict[str, Any]:
        """Prepare context for agents"""
        context = {
            "baseline_date": patient_data.baseline_date.isoformat(),
            "followup_date": patient_data.followup_date.isoformat(),
            "flair_change_pct": patient_data.flair_change_percentage,
            "enhancement_change_pct": patient_data.enhancement_change_percentage,
        }
        
        # Calculate days since radiation if available
        if patient_data.radiation_date and patient_data.followup_date:
            days_diff = (patient_data.followup_date - patient_data.radiation_date).days
            context["days_since_radiation"] = days_diff
        
        return context
    
    def _determine_next_node(self, node: Dict[str, Any], value: Any) -> str:
        """Determine next node based on extracted value"""
        # Map values to next nodes based on node configuration
        return node["next_nodes"].get(str(value), node["default_next"])
    
    def _make_decision(self, node: Dict[str, Any], session: Dict[str, Any]) -> str:
        """Make a decision at a decision node"""
        # Implement decision logic based on node configuration and session state
        # This would use the results from previous agents
        return "default"
    
    def _generate_reasoning(self, session: Dict[str, Any]) -> str:
        """Generate final reasoning from all agent results"""
        reasoning_parts = []
        for agent_name, result_data in session["results"].items():
            if "result" in result_data:
                reasoning_parts.append(
                    f"{agent_name}: {result_data['result'].reasoning}"
                )
        return " → ".join(reasoning_parts)
    
    def _calculate_confidence(self, session: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        confidences = []
        for result_data in session["results"].values():
            if "result" in result_data:
                confidences.append(result_data["result"].confidence)
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    async def _notify_status(
        self,
        patient_id: str,
        status: str,
        data: Dict[str, Any]
    ):
        """Send status update via WebSocket"""
        await self.ws_manager.send_to_patient(
            patient_id,
            {
                "type": status,
                "timestamp": datetime.utcnow().isoformat(),
                **data
            }
        )