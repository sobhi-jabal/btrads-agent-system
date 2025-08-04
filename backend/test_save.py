#!/usr/bin/env python
"""Test script to verify agent result saving"""
import asyncio
from datetime import datetime
from models.agent import AgentResult
from services.agent_service_sqlite import agent_service

async def test_save():
    # Create a test result
    result = AgentResult(
        agent_id="test-agent",
        node_id="test-node",
        patient_id="TEST123",
        timestamp=datetime.utcnow(),
        extracted_value={"test": "value"},
        confidence=0.95,
        reasoning="Test reasoning",
        source_highlights=[],
        processing_time_ms=100,
        llm_model="test-model"
    )
    
    print(f"Saving result: {result}")
    saved = await agent_service.save_result(result)
    print(f"Saved successfully: {saved}")
    
    # Now retrieve it
    results = await agent_service.get_results("TEST123")
    print(f"Retrieved {len(results)} results")
    for r in results:
        print(f"  - {r.agent_id}: {r.extracted_value}")

if __name__ == "__main__":
    asyncio.run(test_save())