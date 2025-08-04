"""
LangGraph-based orchestrator for BT-RADS flowchart
Implements the BT-RADS decision tree as a stateful graph
"""
import logging
from typing import Dict, Any, Optional, List, TypedDict, Annotated
from datetime import datetime
import asyncio
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

from models.patient import PatientData
from models.agent import AgentResult
from models.btrads import BTRADSPath, BTRADSResult, BTRADSScore
from services.websocket_manager import WebSocketManager
from config.agent_config import agent_config
from utils.database import get_async_db, AgentResultRecord
from services.agent_service_sqlite import agent_service

logger = logging.getLogger(__name__)

# Define the state structure for the graph
class BTRADSState(TypedDict):
    """State for BT-RADS processing"""
    # Patient information
    patient_id: str
    patient_data: PatientData
    
    # Processing state
    current_node: str
    path: List[str]
    decisions: Dict[str, Any]
    
    # Agent results
    agent_results: Dict[str, AgentResult]
    
    # Context for agents
    context: Dict[str, Any]
    
    # Final result
    btrads_score: Optional[str]
    reasoning: List[str]
    confidence_scores: List[float]
    
    # Metadata
    started_at: datetime
    completed_at: Optional[datetime]
    
    # Validation state
    pending_validations: List[Dict[str, Any]]
    validation_mode: str  # "auto" or "manual"
    
    # Error tracking
    errors: List[str]
    warnings: List[str]

class LangGraphOrchestrator:
    """Orchestrates BT-RADS processing using LangGraph"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.agents = self._initialize_agents()
        
        # Use memory saver for checkpointing
        self.checkpointer = MemorySaver()
        
        self.graph = self._build_graph()
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize all agents"""
        agents = {}
        agent_types = [
            "prior_assessment",
            "imaging_comparison",
            "medication_status",
            "radiation_timeline",
            "component_analysis",
            "extent_analysis", 
            "progression_pattern"
        ]
        
        for agent_type in agent_types:
            try:
                AgentClass = agent_config.get_agent_class(agent_type)
                agents[agent_type] = AgentClass()
                logger.info(f"Initialized {agent_type} agent")
            except Exception as e:
                logger.error(f"Failed to initialize {agent_type}: {e}")
                raise
        
        return agents
    
    def _build_graph(self) -> StateGraph:
        """Build the BT-RADS flowchart as a LangGraph"""
        
        # Create the graph
        workflow = StateGraph(BTRADSState)
        
        # Add nodes for each decision point
        workflow.add_node("start", self._start_node)
        workflow.add_node("prior_assessment", self._prior_assessment_node)
        workflow.add_node("imaging_comparison", self._imaging_comparison_node)
        workflow.add_node("medication_check", self._medication_check_node)
        workflow.add_node("radiation_check", self._radiation_check_node)
        workflow.add_node("component_analysis", self._component_analysis_node)
        workflow.add_node("extent_analysis", self._extent_analysis_node)
        workflow.add_node("progression_pattern", self._progression_pattern_node)
        
        # Terminal nodes for each BT-RADS score
        workflow.add_node("bt_0", self._terminal_node_bt0)
        workflow.add_node("bt_1a", self._terminal_node_bt1a)
        workflow.add_node("bt_1b", self._terminal_node_bt1b)
        workflow.add_node("bt_2", self._terminal_node_bt2)
        workflow.add_node("bt_3a", self._terminal_node_bt3a)
        workflow.add_node("bt_3b", self._terminal_node_bt3b)
        workflow.add_node("bt_3c", self._terminal_node_bt3c)
        workflow.add_node("bt_4", self._terminal_node_bt4)
        
        # Add edges based on BT-RADS flowchart logic
        workflow.set_entry_point("start")
        
        # From start
        workflow.add_edge("start", "prior_assessment")
        
        # From prior assessment
        workflow.add_conditional_edges(
            "prior_assessment",
            self._route_from_prior,
            {
                "no_prior": "bt_0",
                "has_prior": "imaging_comparison"
            }
        )
        
        # From imaging comparison
        workflow.add_conditional_edges(
            "imaging_comparison",
            self._route_from_imaging,
            {
                "stable": "bt_2",
                "improved": "medication_check",
                "worse": "radiation_check"
            }
        )
        
        # From medication check (for improved cases)
        workflow.add_conditional_edges(
            "medication_check",
            self._route_from_medication,
            {
                "no_meds": "bt_1a",
                "on_avastin": "bt_1b",
                "on_steroids": "bt_1b",
                "unknown": "bt_1a"  # Conservative
            }
        )
        
        # From radiation check (for worse cases)
        workflow.add_conditional_edges(
            "radiation_check",
            self._route_from_radiation,
            {
                "recent": "bt_3a",  # <90 days
                "remote": "component_analysis"
            }
        )
        
        # From component analysis
        workflow.add_conditional_edges(
            "component_analysis",
            self._route_from_component,
            {
                "flair_only": "bt_3b",
                "enhancement": "extent_analysis",
                "mixed": "extent_analysis"
            }
        )
        
        # From extent analysis
        workflow.add_conditional_edges(
            "extent_analysis",
            self._route_from_extent,
            {
                "limited": "bt_3b",
                "extensive": "progression_pattern"
            }
        )
        
        # From progression pattern
        workflow.add_conditional_edges(
            "progression_pattern",
            self._route_from_progression,
            {
                "stable_pattern": "bt_3c",
                "progressive": "bt_4"
            }
        )
        
        # All terminal nodes go to END
        for bt_score in ["bt_0", "bt_1a", "bt_1b", "bt_2", "bt_3a", "bt_3b", "bt_3c", "bt_4"]:
            workflow.add_edge(bt_score, END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    # Node implementations
    async def _start_node(self, state: BTRADSState) -> BTRADSState:
        """Initialize processing"""
        logger.info(f"[DEBUG] Entering _start_node for patient {state.get('patient_id')}")
        state["current_node"] = "start"
        state["path"].append("start")
        
        # Notify WebSocket
        await self._notify_status(state["patient_id"], "processing_started", {
            "patient_id": state["patient_id"],
            "mode": state["validation_mode"]
        })
        
        logger.info(f"[DEBUG] Exiting _start_node for patient {state.get('patient_id')}")
        return state
    
    async def _prior_assessment_node(self, state: BTRADSState) -> BTRADSState:
        """Check for suitable prior imaging"""
        logger.info(f"[DEBUG] Entering _prior_assessment_node for patient {state.get('patient_id')}")
        state["current_node"] = "prior_assessment"
        state["path"].append("prior_assessment")
        
        # Run agent
        agent = self.agents["prior_assessment"]
        logger.info(f"[DEBUG] About to call prior_assessment agent.extract")
        result = await agent.extract(
            clinical_note=state["patient_data"].clinical_note,
            context=state["context"],
            patient_id=state["patient_id"]
        )
        
        # Store result
        state["agent_results"]["prior_assessment"] = result
        # Handle both string and dict extracted_value
        if isinstance(result.extracted_value, dict):
            state["decisions"]["has_prior"] = result.extracted_value.get("has_suitable_prior", False)
        else:
            state["decisions"]["has_prior"] = result.extracted_value
        state["reasoning"].append(f"Prior assessment: {result.reasoning}")
        state["confidence_scores"].append(result.confidence)
        
        # Handle validation if needed
        if state["validation_mode"] == "manual" and result.confidence < 0.8:
            state["pending_validations"].append({
                "node": "prior_assessment",
                "result": result,
                "timestamp": datetime.utcnow()
            })
        
        return state
    
    async def _imaging_comparison_node(self, state: BTRADSState) -> BTRADSState:
        """Compare current imaging to prior"""
        state["current_node"] = "imaging_comparison"
        state["path"].append("imaging_comparison")
        
        # Run agent
        agent = self.agents["imaging_comparison"]
        result = await agent.extract(
            clinical_note=state["patient_data"].clinical_note,
            context=state["context"],
            patient_id=state["patient_id"]
        )
        
        # Store result
        state["agent_results"]["imaging_comparison"] = result
        # Handle both string and dict extracted_value
        if isinstance(result.extracted_value, dict):
            state["decisions"]["imaging_change"] = result.extracted_value.get("overall_assessment", "unknown")
        else:
            # extracted_value is already the assessment string
            state["decisions"]["imaging_change"] = result.extracted_value
        state["reasoning"].append(f"Imaging comparison: {result.reasoning}")
        state["confidence_scores"].append(result.confidence)
        
        return state
    
    async def _medication_check_node(self, state: BTRADSState) -> BTRADSState:
        """Check medication status for improved cases"""
        state["current_node"] = "medication_check"
        state["path"].append("medication_check")
        
        # Run agent
        agent = self.agents["medication_status"]
        result = await agent.extract(
            clinical_note=state["patient_data"].clinical_note,
            context=state["context"],
            patient_id=state["patient_id"]
        )
        
        # Store result
        state["agent_results"]["medication_status"] = result
        state["decisions"]["medication_status"] = result.extracted_value
        state["reasoning"].append(f"Medication status: {result.reasoning}")
        state["confidence_scores"].append(result.confidence)
        
        return state
    
    async def _radiation_check_node(self, state: BTRADSState) -> BTRADSState:
        """Check radiation timeline for worse cases"""
        state["current_node"] = "radiation_check"
        state["path"].append("radiation_check")
        
        # Run agent
        agent = self.agents["radiation_timeline"]
        result = await agent.extract(
            clinical_note=state["patient_data"].clinical_note,
            context=state["context"],
            patient_id=state["patient_id"]
        )
        
        # Store result
        state["agent_results"]["radiation_timeline"] = result
        
        # Calculate days since radiation
        days_since = state["context"].get("days_since_radiation", 999)
        state["decisions"]["days_since_radiation"] = days_since
        state["decisions"]["radiation_recent"] = days_since < 90
        state["reasoning"].append(f"Radiation timeline: {result.reasoning}")
        state["confidence_scores"].append(result.confidence)
        
        return state
    
    async def _component_analysis_node(self, state: BTRADSState) -> BTRADSState:
        """Analyze components (FLAIR vs enhancement)"""
        state["current_node"] = "component_analysis"
        state["path"].append("component_analysis")
        
        # Run agent
        agent = self.agents["component_analysis"]
        result = await agent.extract(
            clinical_note=state["patient_data"].clinical_note,
            context=state["context"],
            patient_id=state["patient_id"]
        )
        
        # Store result
        state["agent_results"]["component_analysis"] = result
        # Handle both string and dict extracted_value
        if isinstance(result.extracted_value, dict):
            state["decisions"]["component_pattern"] = result.extracted_value.get("pattern", "unknown")
        else:
            state["decisions"]["component_pattern"] = result.extracted_value
        state["reasoning"].append(f"Component analysis: {result.reasoning}")
        state["confidence_scores"].append(result.confidence)
        
        return state
    
    async def _extent_analysis_node(self, state: BTRADSState) -> BTRADSState:
        """Analyze extent of changes (40% rule)"""
        state["current_node"] = "extent_analysis"
        state["path"].append("extent_analysis")
        
        # Run agent
        agent = self.agents["extent_analysis"]
        result = await agent.extract(
            clinical_note=state["patient_data"].clinical_note,
            context=state["context"],
            patient_id=state["patient_id"]
        )
        
        # Store result
        state["agent_results"]["extent_analysis"] = result
        # Handle both string and dict extracted_value
        if isinstance(result.extracted_value, dict):
            state["decisions"]["extent"] = result.extracted_value.get("extent", "unknown")
        else:
            state["decisions"]["extent"] = result.extracted_value
        state["reasoning"].append(f"Extent analysis: {result.reasoning}")
        state["confidence_scores"].append(result.confidence)
        
        return state
    
    async def _progression_pattern_node(self, state: BTRADSState) -> BTRADSState:
        """Analyze progression pattern"""
        state["current_node"] = "progression_pattern"
        state["path"].append("progression_pattern")
        
        # Run agent
        agent = self.agents["progression_pattern"]
        result = await agent.extract(
            clinical_note=state["patient_data"].clinical_note,
            context=state["context"],
            patient_id=state["patient_id"]
        )
        
        # Store result
        state["agent_results"]["progression_pattern"] = result
        # Handle both string and dict extracted_value
        if isinstance(result.extracted_value, dict):
            state["decisions"]["progression_pattern"] = result.extracted_value.get("pattern", "unknown")
        else:
            state["decisions"]["progression_pattern"] = result.extracted_value
        state["reasoning"].append(f"Progression pattern: {result.reasoning}")
        state["confidence_scores"].append(result.confidence)
        
        return state
    
    # Terminal nodes
    async def _terminal_node_bt0(self, state: BTRADSState) -> BTRADSState:
        state["btrads_score"] = "0"
        state["reasoning"].append("No suitable prior for comparison")
        state["completed_at"] = datetime.utcnow()
        return state
    
    async def _terminal_node_bt1a(self, state: BTRADSState) -> BTRADSState:
        state["btrads_score"] = "BT-1a"
        state["reasoning"].append("Improved without confounding medication effects")
        state["completed_at"] = datetime.utcnow()
        return state
    
    async def _terminal_node_bt1b(self, state: BTRADSState) -> BTRADSState:
        state["btrads_score"] = "BT-1b"
        state["reasoning"].append("Improved but with confounding medication effects")
        state["completed_at"] = datetime.utcnow()
        return state
    
    async def _terminal_node_bt2(self, state: BTRADSState) -> BTRADSState:
        state["btrads_score"] = "BT-2"
        state["reasoning"].append("Stable disease")
        state["completed_at"] = datetime.utcnow()
        return state
    
    async def _terminal_node_bt3a(self, state: BTRADSState) -> BTRADSState:
        state["btrads_score"] = "BT-3a"
        state["reasoning"].append("Worsening within 90 days of radiation")
        state["completed_at"] = datetime.utcnow()
        return state
    
    async def _terminal_node_bt3b(self, state: BTRADSState) -> BTRADSState:
        state["btrads_score"] = "BT-3b"
        state["reasoning"].append("Treatment effect favored over progression")
        state["completed_at"] = datetime.utcnow()
        return state
    
    async def _terminal_node_bt3c(self, state: BTRADSState) -> BTRADSState:
        state["btrads_score"] = "BT-3c"
        state["reasoning"].append("Equivocal findings")
        state["completed_at"] = datetime.utcnow()
        return state
    
    async def _terminal_node_bt4(self, state: BTRADSState) -> BTRADSState:
        state["btrads_score"] = "BT-4"
        state["reasoning"].append("Progressive disease")
        state["completed_at"] = datetime.utcnow()
        return state
    
    # Routing functions
    def _route_from_prior(self, state: BTRADSState) -> str:
        """Route from prior assessment node"""
        if state["decisions"].get("has_prior", False):
            return "has_prior"
        return "no_prior"
    
    def _route_from_imaging(self, state: BTRADSState) -> str:
        """Route from imaging comparison node"""
        assessment = state["decisions"].get("imaging_change", "unknown")
        if assessment == "improved":
            return "improved"
        elif assessment == "stable":
            return "stable"
        else:
            return "worse"
    
    def _route_from_medication(self, state: BTRADSState) -> str:
        """Route from medication check node"""
        med_status = state["decisions"].get("medication_status", {})
        
        if med_status.get("avastin_status") in ["ongoing", "first_treatment", "started"]:
            return "on_avastin"
        elif med_status.get("steroid_status") in ["increasing", "started"]:
            return "on_steroids"
        elif (med_status.get("avastin_status") == "none" and 
              med_status.get("steroid_status") in ["none", "stable", "decreasing"]):
            return "no_meds"
        else:
            return "unknown"
    
    def _route_from_radiation(self, state: BTRADSState) -> str:
        """Route from radiation check node"""
        if state["decisions"].get("radiation_recent", False):
            return "recent"
        return "remote"
    
    def _route_from_component(self, state: BTRADSState) -> str:
        """Route from component analysis node"""
        pattern = state["decisions"].get("component_pattern", "unknown")
        if pattern == "flair_only":
            return "flair_only"
        elif pattern in ["enhancement", "mixed"]:
            return "enhancement"
        else:
            return "enhancement"  # Default
    
    def _route_from_extent(self, state: BTRADSState) -> str:
        """Route from extent analysis node"""
        extent = state["decisions"].get("extent", "unknown")
        if extent == "limited":
            return "limited"
        return "extensive"
    
    def _route_from_progression(self, state: BTRADSState) -> str:
        """Route from progression pattern node"""
        pattern = state["decisions"].get("progression_pattern", "unknown")
        if pattern == "progressive":
            return "progressive"
        return "stable_pattern"
    
    # Public methods
    async def process_patient(
        self,
        patient_data: PatientData,
        validation_mode: str = "auto"
    ) -> BTRADSResult:
        """Process a patient through the BT-RADS flowchart"""
        
        logger.info(f"[Orchestrator] Starting processing for patient {patient_data.patient_id}")
        
        # Initialize state
        initial_state = BTRADSState(
            patient_id=patient_data.patient_id,
            patient_data=patient_data,
            current_node="start",
            path=[],
            decisions={},
            agent_results={},
            context=self._prepare_context(patient_data),
            btrads_score=None,
            reasoning=[],
            confidence_scores=[],
            started_at=datetime.utcnow(),
            completed_at=None,
            pending_validations=[],
            validation_mode=validation_mode,
            errors=[],
            warnings=[]
        )
        
        logger.info(f"[Orchestrator] Created initial state for {patient_data.patient_id}")
        
        # Run the graph
        config = {"configurable": {"thread_id": patient_data.patient_id}}
        logger.info(f"[Orchestrator] Invoking graph for {patient_data.patient_id}")
        final_state = await self.graph.ainvoke(initial_state, config)
        logger.info(f"[Orchestrator] Graph completed for {patient_data.patient_id}")
        
        # Create result
        return await self._create_result(final_state)
    
    def _prepare_context(self, patient_data: PatientData) -> Dict[str, Any]:
        """Prepare context for agents"""
        context = {
            "baseline_date": patient_data.baseline_date.isoformat() if patient_data.baseline_date else None,
            "followup_date": patient_data.followup_date.isoformat() if patient_data.followup_date else None,
            "flair_change_pct": patient_data.flair_change_percentage,
            "enhancement_change_pct": patient_data.enhancement_change_percentage,
        }
        
        # Calculate days since radiation if available
        if patient_data.radiation_date and patient_data.followup_date:
            days_diff = (patient_data.followup_date - patient_data.radiation_date).days
            context["days_since_radiation"] = days_diff
        
        return context
    
    async def _create_result(self, state: BTRADSState) -> BTRADSResult:
        """Create final result from state"""
        
        # Save all agent results to database before creating final result
        for agent_name, result in state["agent_results"].items():
            if result:
                await self._save_agent_result(result)
        
        # Calculate average confidence
        avg_confidence = (
            sum(state["confidence_scores"]) / len(state["confidence_scores"])
            if state["confidence_scores"] else 0.0
        )
        
        # Create path object
        path = BTRADSPath(patient_id=state["patient_id"])
        for node in state["path"]:
            path.add_node(node, state["decisions"].get(node))
        
        # Handle both formats (with and without BT- prefix)
        score_value = state["btrads_score"]
        if score_value and score_value.startswith("BT-"):
            score_value = score_value[3:]  # Remove "BT-" prefix
        
        # Convert medication_status dict to string if needed
        med_status = state["decisions"].get("medication_status")
        if isinstance(med_status, dict):
            # Format as string: "Steroids: status, Avastin: status"
            steroid_status = med_status.get("steroid_status", "unknown")
            avastin_status = med_status.get("avastin_status", "unknown")
            medication_effects_str = f"Steroids: {steroid_status}, Avastin: {avastin_status}"
        else:
            medication_effects_str = med_status
        
        return BTRADSResult(
            patient_id=state["patient_id"],
            score=BTRADSScore(score_value) if score_value else None,
            reasoning=" → ".join(state["reasoning"]),
            algorithm_path=path,
            volume_assessment=state["decisions"].get("imaging_change"),
            medication_effects=medication_effects_str,
            time_since_radiation=state["context"].get("days_since_radiation"),
            total_validations=len([v for v in state["pending_validations"] if v.get("validated")]),
            modifications_made=0,  # TODO: Track modifications
            confidence_score=avg_confidence,
            started_at=state["started_at"],
            completed_at=state["completed_at"],
            processing_duration_seconds=(
                (state["completed_at"] - state["started_at"]).total_seconds()
                if state["completed_at"] else 0
            )
        )
    
    async def _save_agent_result(self, result: AgentResult):
        """Save an agent result to the database"""
        try:
            await agent_service.save_result(result)
            logger.info(f"Saved agent result for {result.agent_id} - patient {result.patient_id}")
        except Exception as e:
            logger.error(f"Failed to save agent result: {e}")
            # Don't fail the whole process if we can't save one result
    
    async def _notify_status(
        self,
        patient_id: str,
        status: str,
        data: Dict[str, Any]
    ):
        """Send status update via WebSocket (non-blocking)"""
        try:
            # Don't await - fire and forget to avoid blocking if no websocket connected
            asyncio.create_task(self.ws_manager.send_to_patient(
                patient_id,
                {
                    "type": status,
                    "timestamp": datetime.utcnow().isoformat(),
                    **data
                }
            ))
        except Exception as e:
            logger.debug(f"WebSocket notification failed (non-critical): {e}")