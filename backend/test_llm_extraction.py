#!/usr/bin/env python3
"""
Test script to verify LLM extraction is working
Run this to see actual LLM output without the validation UI
"""
import asyncio
import json
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from models.patient import PatientData
from config.agent_config import agent_config

# Sample clinical note
TEST_CLINICAL_NOTE = """
CLINICAL HISTORY: 56-year-old male with glioblastoma, status post resection.

CURRENT MEDICATIONS:
- Dexamethasone 4mg BID (increased from 2mg BID due to worsening edema)
- Keppra 500mg BID
- Avastin (bevacizumab) 10mg/kg IV every 2 weeks, currently on cycle #3

COMPARISON: MRI brain from 3/15/2024

FINDINGS:
Post-surgical cavity in right temporal lobe. FLAIR signal has increased by approximately 
25% compared to prior. Enhancement along the cavity margins has also increased.
"""

async def test_direct_agent():
    """Test agent directly without orchestration"""
    print("Testing Direct Agent Extraction")
    print("=" * 60)
    
    # Get medication status agent
    agent_class = agent_config.get_agent_class("medication_status")
    agent = agent_class()
    
    print(f"Using agent mode: {agent_config.mode.value}")
    print(f"Agent class: {agent.__class__.__name__}")
    
    # Create context
    context = {
        "baseline_date": "2024-03-15",
        "followup_date": "2024-05-15",
        "flair_change_pct": 25.0,
        "enhancement_change_pct": 30.0
    }
    
    # Run extraction
    print("\nRunning extraction...")
    start_time = datetime.now()
    
    try:
        result = await agent.extract(
            clinical_note=TEST_CLINICAL_NOTE,
            context=context,
            patient_id="test-001"
        )
        
        print(f"\n✅ Extraction completed in {result.processing_time_ms}ms")
        print(f"LLM Model: {result.llm_model}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"\nExtracted Value:")
        print(json.dumps(result.extracted_value, indent=2))
        print(f"\nReasoning: {result.reasoning}")
        
        if result.source_highlights:
            print("\nSource Highlights:")
            for highlight in result.source_highlights:
                print(f"  - '{highlight.text[:100]}...' (confidence: {highlight.confidence:.2f})")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_with_orchestrator():
    """Test with orchestrator in auto-validate mode"""
    print("\n\nTesting With Orchestrator (Auto-Validate)")
    print("=" * 60)
    
    from agents.orchestration.agent_orchestrator import AgentOrchestrator
    from services.websocket_manager import WebSocketManager
    
    # Create mock websocket manager
    ws_manager = WebSocketManager()
    
    # Create orchestrator
    orchestrator = AgentOrchestrator(ws_manager)
    
    # Create patient data
    patient_data = PatientData(
        patient_id="test-002",
        clinical_note=TEST_CLINICAL_NOTE,
        baseline_date=datetime(2024, 3, 15),
        followup_date=datetime(2024, 5, 15),
        baseline_flair_volume=100.0,
        followup_flair_volume=125.0,
        baseline_enhancement_volume=50.0,
        followup_enhancement_volume=65.0,
        flair_change_percentage=25.0,
        enhancement_change_percentage=30.0
    )
    
    # Process with auto-validate = True
    print("Processing with auto_validate=True...")
    
    # We'll need to handle the async processing differently
    # since it uses WebSocket notifications
    
    # For now, just test the agent initialization
    print(f"Orchestrator has {len(orchestrator.agents)} agents:")
    for name, agent in orchestrator.agents.items():
        print(f"  - {name}: {agent.__class__.__name__}")

async def check_services():
    """Check if required services are running"""
    print("Checking Services")
    print("=" * 60)
    
    from utils.startup_checks import StartupChecker
    
    checker = StartupChecker()
    
    # Check vLLM
    vllm_ok = await checker.check_vllm_service()
    print(f"vLLM Service: {'✅ Available' if vllm_ok else '❌ Not Available'}")
    
    # Check Ollama
    ollama_ok = await checker.check_ollama_service()
    print(f"Ollama Service: {'✅ Available' if ollama_ok else '❌ Not Available'}")
    
    # Determine mode
    if agent_config.mode.value == "vllm" and not vllm_ok:
        print("\n⚠️  WARNING: Configured for vLLM but service not available!")
        print("The system may fall back to mock mode.")

async def main():
    """Run all tests"""
    print("BT-RADS LLM Extraction Test")
    print("=" * 60)
    print(f"Environment: AGENT_MODE={os.getenv('AGENT_MODE', 'not set')}")
    print(f"Current Mode: {agent_config.mode.value}")
    print()
    
    # Check services
    await check_services()
    
    # Test direct agent
    await test_direct_agent()
    
    # Test with orchestrator
    await test_with_orchestrator()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    
    print("\n💡 TIP: If you're seeing mock results:")
    print("1. Ensure vLLM is running: docker-compose -f docker-compose.vllm.yml up")
    print("2. Or ensure Ollama is running: ollama serve")
    print("3. Check AGENT_MODE in .env file")
    print("4. Look for fallback warnings in the logs")

if __name__ == "__main__":
    asyncio.run(main())