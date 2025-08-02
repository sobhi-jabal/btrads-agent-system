"""
Test script for vLLM integration
Run this to verify vLLM is working correctly
"""
import asyncio
import json
from datetime import datetime

# Add parent directory to path
import sys
sys.path.append('..')

from services.vllm_service import VLLMService, VLLMConfig
from agents.extraction.medication_status_vllm import MedicationStatusAgent

# Sample clinical note for testing
SAMPLE_NOTE = """
CLINICAL HISTORY: 45-year-old male with glioblastoma, status post resection and chemoradiation.

CURRENT MEDICATIONS:
- Dexamethasone 4mg BID (increased from 2mg BID last visit due to worsening edema)
- Keppra 500mg BID for seizure prophylaxis
- Started on Avastin (bevacizumab) 10mg/kg IV, this is cycle #3

RADIATION HISTORY:
Completed concurrent chemoradiation on March 15, 2024. Total dose 60 Gy in 30 fractions.

COMPARISON: MRI brain from 2 months ago.

FINDINGS:
Post-surgical cavity in the right temporal lobe with increased peripheral FLAIR signal 
compared to prior, now measuring 4.2 x 3.1 cm (previously 3.5 x 2.8 cm). 
Enhancement along the cavity margins has also increased.
"""

async def test_vllm_service():
    """Test vLLM service directly"""
    print("Testing vLLM Service...")
    print("=" * 50)
    
    config = VLLMConfig()
    
    async with VLLMService(config) as vllm:
        # List available models
        models = await vllm.list_models()
        print(f"Available models: {models}")
        
        # Test chat completion
        messages = [
            {"role": "system", "content": "You are a helpful medical assistant."},
            {"role": "user", "content": "What is BT-RADS?"}
        ]
        
        print("\nTesting chat completion...")
        response = await vllm.chat_completion(messages, model="mixtral-8x7b")
        print(f"Response: {response['choices'][0]['message']['content'][:200]}...")
        
        # Test medical extraction
        print("\nTesting medical extraction...")
        result = await vllm.extract_btrads_info(
            clinical_note=SAMPLE_NOTE,
            extraction_type="medication_status",
            context={"followup_date": "2024-05-15"}
        )
        
        print(f"Extraction result:")
        print(json.dumps(result, indent=2))

async def test_medication_agent():
    """Test medication status agent"""
    print("\n\nTesting Medication Status Agent...")
    print("=" * 50)
    
    agent = MedicationStatusAgent()
    
    context = {
        "baseline_date": "2024-03-15",
        "followup_date": "2024-05-15",
        "days_since_radiation": 61
    }
    
    result = await agent.extract(
        clinical_note=SAMPLE_NOTE,
        context=context,
        patient_id="test-001"
    )
    
    print(f"Agent: {result.agent_id}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Extracted value: {result.extracted_value}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Processing time: {result.processing_time_ms}ms")
    print(f"LLM model: {result.llm_model}")
    
    if result.source_highlights:
        print("\nSource highlights:")
        for highlight in result.source_highlights:
            print(f"  - '{highlight.text}' (confidence: {highlight.confidence:.2f})")
    
    if result.missing_info:
        print("\nMissing information:")
        for missing in result.missing_info:
            print(f"  - {missing.field}: {missing.reason}")

async def test_error_handling():
    """Test error handling and fallbacks"""
    print("\n\nTesting Error Handling...")
    print("=" * 50)
    
    # Test with empty note
    agent = MedicationStatusAgent()
    result = await agent.extract(
        clinical_note="",
        context={},
        patient_id="test-error"
    )
    
    print(f"Empty note result: {result.extracted_value}")
    print(f"Confidence: {result.confidence}")
    
    # Test with nonsense note
    result = await agent.extract(
        clinical_note="This is not a medical note at all.",
        context={},
        patient_id="test-nonsense"
    )
    
    print(f"\nNonsense note result: {result.extracted_value}")
    print(f"Confidence: {result.confidence}")

async def main():
    """Run all tests"""
    print("BT-RADS vLLM Integration Test")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    print()
    
    try:
        # Test vLLM service
        await test_vllm_service()
        
        # Test medication agent
        await test_medication_agent()
        
        # Test error handling
        await test_error_handling()
        
        print("\n" + "=" * 70)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\n\nError during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())