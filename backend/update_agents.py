#!/usr/bin/env python3
"""Quick script to update all agent files to use Ollama"""
import os
import re

agent_files = [
    "imaging_comparison.py",
    "radiation_timeline.py", 
    "component_analysis.py",
    "extent_analysis.py",
    "progression_pattern.py"
]

for filename in agent_files:
    filepath = f"agents/extraction/{filename}"
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Update _call_llm to include output_format
        content = re.sub(
            r'response = await self\._call_llm\(prompt\)',
            'response = await self._call_llm(prompt, output_format="json")',
            content
        )
        
        # Update llm_model from mock-llm to phi4:14b
        content = re.sub(
            r'llm_model="mock-llm"',
            'llm_model="phi4:14b"',
            content
        )
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"Updated {filename}")

print("Done!")