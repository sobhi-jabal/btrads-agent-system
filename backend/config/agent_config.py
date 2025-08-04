"""
Agent configuration for BT-RADS system
Manages agent selection between mock and vLLM implementations
"""
import os
from typing import Dict, Any
from enum import Enum

class AgentMode(Enum):
    """Agent implementation modes"""
    MOCK = "mock"
    VLLM = "vllm"
    OLLAMA = "ollama"

class OrchestratorMode(Enum):
    """Orchestrator implementation modes"""
    SIMPLE = "simple"
    LANGGRAPH = "langgraph"

class AgentConfig:
    """Configuration for agent system"""
    
    def __init__(self):
        # Default to vLLM mode
        self.mode = AgentMode(os.getenv("AGENT_MODE", "vllm"))
        
        # Orchestrator mode
        self.orchestrator_mode = OrchestratorMode(os.getenv("ORCHESTRATOR_MODE", "langgraph"))
        
        # vLLM configuration
        self.vllm_config = {
            "base_url": os.getenv("VLLM_BASE_URL", "http://localhost:8000"),
            "api_key": os.getenv("VLLM_API_KEY"),
            "timeout": int(os.getenv("VLLM_TIMEOUT", "120")),
            "max_retries": int(os.getenv("VLLM_MAX_RETRIES", "3"))
        }
        
        # Ollama configuration (fallback)
        self.ollama_config = {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": os.getenv("OLLAMA_MODEL", "phi4:14b")
        }
        
        # Agent-specific configurations
        self.agent_configs = {
            "prior_assessment": {
                "complexity": "low",
                "max_tokens": 512,
                "temperature": 0.1
            },
            "imaging_comparison": {
                "complexity": "high",
                "max_tokens": 1024,
                "temperature": 0.1
            },
            "medication_status": {
                "complexity": "medium",
                "max_tokens": 768,
                "temperature": 0.1
            },
            "radiation_timeline": {
                "complexity": "medium",
                "max_tokens": 512,
                "temperature": 0.1
            },
            "component_analysis": {
                "complexity": "high",
                "max_tokens": 1024,
                "temperature": 0.2
            },
            "extent_analysis": {
                "complexity": "high",
                "max_tokens": 1024,
                "temperature": 0.2
            },
            "progression_pattern": {
                "complexity": "high",
                "max_tokens": 1280,
                "temperature": 0.2
            }
        }
    
    def get_agent_class(self, agent_type: str):
        """Get the appropriate agent class based on mode"""
        
        if self.mode == AgentMode.VLLM:
            # Import vLLM implementations
            if agent_type == "medication_status":
                from agents.extraction.medication_status_vllm import MedicationStatusAgent
                return MedicationStatusAgent
            elif agent_type == "prior_assessment":
                from agents.extraction.prior_assessment_vllm import PriorAssessmentAgent
                return PriorAssessmentAgent
            elif agent_type == "imaging_comparison":
                from agents.extraction.imaging_comparison_vllm import ImagingComparisonAgent
                return ImagingComparisonAgent
            elif agent_type == "radiation_timeline":
                from agents.extraction.radiation_timeline_vllm import RadiationTimelineAgent
                return RadiationTimelineAgent
            elif agent_type == "component_analysis":
                from agents.extraction.component_analysis_vllm import ComponentAnalysisAgent
                return ComponentAnalysisAgent
            elif agent_type == "extent_analysis":
                from agents.extraction.extent_analysis_vllm import ExtentAnalysisAgent
                return ExtentAnalysisAgent
            elif agent_type == "progression_pattern":
                from agents.extraction.progression_pattern_vllm import ProgressionPatternAgent
                return ProgressionPatternAgent
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
                
        elif self.mode == AgentMode.MOCK:
            # Import mock implementations (original)
            if agent_type == "medication_status":
                from agents.extraction.medication_status import MedicationStatusAgent
                return MedicationStatusAgent
            elif agent_type == "prior_assessment":
                from agents.extraction.prior_assessment import PriorAssessmentAgent
                return PriorAssessmentAgent
            elif agent_type == "imaging_comparison":
                from agents.extraction.imaging_comparison import ImagingComparisonAgent
                return ImagingComparisonAgent
            elif agent_type == "radiation_timeline":
                from agents.extraction.radiation_timeline import RadiationTimelineAgent
                return RadiationTimelineAgent
            elif agent_type == "component_analysis":
                from agents.extraction.component_analysis import ComponentAnalysisAgent
                return ComponentAnalysisAgent
            elif agent_type == "extent_analysis":
                from agents.extraction.extent_analysis import ExtentAnalysisAgent
                return ExtentAnalysisAgent
            elif agent_type == "progression_pattern":
                from agents.extraction.progression_pattern import ProgressionPatternAgent
                return ProgressionPatternAgent
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
        
        else:
            # Ollama mode - use mock agents for now (they work without external dependencies)
            # In production, these would be replaced with Ollama-specific implementations
            if agent_type == "medication_status":
                from agents.extraction.medication_status import MedicationStatusAgent
                return MedicationStatusAgent
            elif agent_type == "prior_assessment":
                from agents.extraction.prior_assessment import PriorAssessmentAgent
                return PriorAssessmentAgent
            elif agent_type == "imaging_comparison":
                from agents.extraction.imaging_comparison import ImagingComparisonAgent
                return ImagingComparisonAgent
            elif agent_type == "radiation_timeline":
                from agents.extraction.radiation_timeline import RadiationTimelineAgent
                return RadiationTimelineAgent
            elif agent_type == "component_analysis":
                from agents.extraction.component_analysis import ComponentAnalysisAgent
                return ComponentAnalysisAgent
            elif agent_type == "extent_analysis":
                from agents.extraction.extent_analysis import ExtentAnalysisAgent
                return ExtentAnalysisAgent
            elif agent_type == "progression_pattern":
                from agents.extraction.progression_pattern import ProgressionPatternAgent
                return ProgressionPatternAgent
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
    
    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """Get configuration for specific agent"""
        return self.agent_configs.get(agent_type, {})
    
    def is_production_mode(self) -> bool:
        """Check if running in production mode (vLLM)"""
        return self.mode == AgentMode.VLLM
    
    def get_embedding_model(self) -> str:
        """Get embedding model for source highlighting"""
        if self.is_production_mode():
            return "sentence-transformers/all-mpnet-base-v2"
        else:
            return "sentence-transformers/all-MiniLM-L6-v2"
    
    def get_orchestrator_class(self):
        """Get the appropriate orchestrator class based on mode"""
        if self.orchestrator_mode == OrchestratorMode.LANGGRAPH:
            from agents.orchestration.langgraph_orchestrator import LangGraphOrchestrator
            return LangGraphOrchestrator
        else:
            from agents.orchestration.agent_orchestrator import AgentOrchestrator
            return AgentOrchestrator
    
    def use_langgraph(self) -> bool:
        """Check if using LangGraph orchestration"""
        return self.orchestrator_mode == OrchestratorMode.LANGGRAPH

# Singleton instance
agent_config = AgentConfig()