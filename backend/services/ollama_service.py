"""
Ollama LLM service for medical text extraction
Uses phi4:14b model for extracting medications and radiation dates
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

import ollama
from ollama import Options

logger = logging.getLogger(__name__)

# BT-RADS configuration prompts (from btrads_main_old.py)
BTRADS_CONFIG = {
    "medication_status": {
        "system_message": "You are an expert medical data extractor specializing in brain tumor patient medication management.",
        "instruction": """Extract CURRENT medication status from the clinical note with high precision.

STEROID STATUS - Look for dexamethasone, decadron, prednisolone, prednisone:
- 'none': Patient is not currently on steroids
- 'stable': Patient continues on same steroid dose  
- 'increasing': Steroid dose being increased/escalated
- 'decreasing': Steroid dose being tapered/decreased
- 'started': Patient newly started on steroids
- 'unknown': Cannot determine from available information

AVASTIN STATUS - Look for Avastin, bevacizumab, BV, anti-angiogenic therapy:
- 'none': Patient is not on Avastin therapy
- 'ongoing': Patient continuing established Avastin therapy
- 'first_treatment': This is clearly the patient's first Avastin dose/cycle
- 'started': Recently started Avastin therapy  
- 'unknown': Cannot determine from available information

Focus on CURRENT status only. Be conservative - use 'unknown' if uncertain.

Return ONLY: {"steroid_status": "X", "avastin_status": "Y"}""",
        "output_format": "json", 
        "json_key": "medication_status",
    },
    
    "radiation_date": {
        "system_message": "You are an expert medical data extractor specializing in brain tumor treatment timelines.",
        "instruction": """Find when this patient completed their most recent radiation therapy course.

Look for: radiation therapy completion, end of XRT, chemoradiation finished, last radiation dose.

Be precise about COMPLETION date, not start date.

Return ONLY: {"radiation_date": "MM/DD/YYYY"} or {"radiation_date": "unknown"}""",
        "output_format": "json", 
        "json_key": "radiation_date",
    }
}


class OllamaExtractionService:
    """Service for extracting medical information using Ollama LLM"""
    
    def __init__(self, model: str = "phi4:14b"):
        self.model = model
        self.base_url = "http://localhost:11434"
        self._ensure_model_available()
    
    def _ensure_model_available(self):
        """Check if model is available, pull if not"""
        try:
            available_models = [m["model"] for m in ollama.list()["models"]]
            if self.model not in available_models:
                logger.info(f"Pulling model {self.model}...")
                ollama.pull(self.model)
                logger.info(f"Model {self.model} pulled successfully")
        except Exception as e:
            logger.error(f"Error checking/pulling model: {e}")
    
    async def extract_medications(self, clinical_note: str) -> Dict[str, Any]:
        """Extract medication status from clinical note"""
        try:
            start_time = datetime.now()
            
            # Get configuration
            config = BTRADS_CONFIG["medication_status"]
            
            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": config["system_message"]
                },
                {
                    "role": "user",
                    "content": f"{config['instruction']}\n\nCLINICAL NOTE:\n{clinical_note}"
                }
            ]
            
            # Call Ollama
            response = await self._call_ollama(messages, output_format="json")
            
            # Parse response
            result = self._parse_medication_response(response)
            
            # Extract evidence
            evidence = self._extract_medication_evidence(clinical_note, result)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "data": result,
                "evidence": evidence,
                "confidence": self._calculate_confidence(result),
                "processing_time": processing_time,
                "method": "llm",
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Error extracting medications: {e}")
            return {
                "data": {"steroid_status": "unknown", "avastin_status": "unknown"},
                "evidence": [],
                "confidence": 0.0,
                "error": str(e),
                "method": "llm",
                "model": self.model
            }
    
    async def extract_radiation_date(self, clinical_note: str) -> Dict[str, Any]:
        """Extract radiation completion date from clinical note"""
        try:
            start_time = datetime.now()
            
            # Get configuration
            config = BTRADS_CONFIG["radiation_date"]
            
            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": config["system_message"]
                },
                {
                    "role": "user",
                    "content": f"{config['instruction']}\n\nCLINICAL NOTE:\n{clinical_note}"
                }
            ]
            
            # Call Ollama
            response = await self._call_ollama(messages, output_format="json")
            
            # Parse response
            result = self._parse_radiation_response(response)
            
            # Extract evidence
            evidence = self._extract_radiation_evidence(clinical_note, result.get("radiation_date"))
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "data": result,
                "evidence": evidence,
                "confidence": self._calculate_date_confidence(result.get("radiation_date")),
                "processing_time": processing_time,
                "method": "llm",
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Error extracting radiation date: {e}")
            return {
                "data": {"radiation_date": "unknown"},
                "evidence": [],
                "confidence": 0.0,
                "error": str(e),
                "method": "llm",
                "model": self.model
            }
    
    async def _call_ollama(self, messages: List[Dict], output_format: str = None) -> str:
        """Call Ollama API with retry logic"""
        options = Options(
            temperature=0.1,  # Low temperature for consistency
            top_k=40,
            top_p=0.95,
            num_ctx=8192,
            num_predict=256,
            repeat_penalty=1.1,
            seed=42,
        )
        
        for attempt in range(3):
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=messages,
                    format="json" if output_format == "json" else None,
                    options=options,
                    keep_alive="10m"
                )
                
                content = response["message"]["content"]
                if not content.strip():
                    raise ValueError("Empty response from Ollama")
                
                return content
                
            except Exception as e:
                logger.warning(f"Ollama attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def _parse_medication_response(self, response: str) -> Dict[str, str]:
        """Parse medication extraction response with fallback handling"""
        try:
            # Try direct JSON parsing
            data = json.loads(response)
            
            # Handle nested structure
            if "medication_status" in data and isinstance(data["medication_status"], dict):
                return data["medication_status"]
            
            # Direct structure
            return {
                "steroid_status": data.get("steroid_status", "unknown"),
                "avastin_status": data.get("avastin_status", "unknown")
            }
            
        except json.JSONDecodeError:
            # Fallback: Extract from text
            result = {"steroid_status": "unknown", "avastin_status": "unknown"}
            
            # Try to extract values using regex
            steroid_match = re.search(r'"steroid_status":\s*"([^"]+)"', response)
            if steroid_match:
                result["steroid_status"] = steroid_match.group(1)
            
            avastin_match = re.search(r'"avastin_status":\s*"([^"]+)"', response)
            if avastin_match:
                result["avastin_status"] = avastin_match.group(1)
            
            return result
    
    def _parse_radiation_response(self, response: str) -> Dict[str, str]:
        """Parse radiation date extraction response"""
        try:
            data = json.loads(response)
            return {"radiation_date": data.get("radiation_date", "unknown")}
            
        except json.JSONDecodeError:
            # Fallback: Extract date using regex
            date_match = re.search(r'"radiation_date":\s*"([^"]+)"', response)
            if date_match:
                return {"radiation_date": date_match.group(1)}
            
            # Try to find date pattern
            date_pattern = re.search(r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b', response)
            if date_pattern:
                return {"radiation_date": date_pattern.group(1)}
            
            return {"radiation_date": "unknown"}
    
    def _extract_medication_evidence(self, text: str, result: Dict[str, str]) -> List[Dict]:
        """Extract evidence snippets for medication findings"""
        evidence = []
        
        # Define search patterns
        steroid_patterns = [
            r'(?i)(dexamethasone|decadron|steroid|prednis\w+)[\s\w]*(?:dose|mg|increased|decreased|started|stopped)',
            r'(?i)(?:increase|decrease|taper|escalat\w+|start\w+)[\s\w]*(?:dexamethasone|decadron|steroid)',
        ]
        
        avastin_patterns = [
            r'(?i)(avastin|bevacizumab|BV)[\s\w]*(?:dose|mg|cycle|infusion|started|ongoing)',
            r'(?i)(?:first|initial|continue|ongoing)[\s\w]*(?:avastin|bevacizumab)',
        ]
        
        # Extract steroid evidence
        for pattern in steroid_patterns:
            for match in re.finditer(pattern, text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                evidence.append({
                    "type": "steroid",
                    "text": text[start:end],
                    "pattern": pattern,
                    "confidence": 0.8
                })
        
        # Extract Avastin evidence
        for pattern in avastin_patterns:
            for match in re.finditer(pattern, text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                evidence.append({
                    "type": "avastin",
                    "text": text[start:end],
                    "pattern": pattern,
                    "confidence": 0.8
                })
        
        return evidence[:5]  # Limit to top 5 evidence items
    
    def _extract_radiation_evidence(self, text: str, radiation_date: str) -> List[Dict]:
        """Extract evidence snippets for radiation date"""
        evidence = []
        
        # Define search patterns
        patterns = [
            r'(?i)radiation[\s\w]*(?:complet\w+|finish\w+|end\w+)[\s\w]*(\d{1,2}/\d{1,2}/\d{2,4})',
            r'(?i)(?:XRT|RT|radiotherapy)[\s\w]*(?:complet\w+|finish\w+)[\s\w]*(\d{1,2}/\d{1,2}/\d{2,4})',
            r'(?i)(\d{1,2}/\d{1,2}/\d{2,4})[\s\w]*radiation[\s\w]*(?:complet\w+|finish\w+)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                evidence.append({
                    "type": "radiation_date",
                    "text": text[start:end],
                    "date_found": match.group(1) if match.groups() else None,
                    "pattern": pattern,
                    "confidence": 0.9
                })
        
        return evidence[:3]
    
    def _calculate_confidence(self, result: Dict[str, str]) -> float:
        """Calculate confidence score for medication extraction"""
        confidence = 1.0
        
        if result.get("steroid_status") == "unknown":
            confidence -= 0.3
        if result.get("avastin_status") == "unknown":
            confidence -= 0.3
            
        return max(0.1, confidence)
    
    def _calculate_date_confidence(self, date: str) -> float:
        """Calculate confidence score for date extraction"""
        if date == "unknown":
            return 0.1
        
        # Check if date format is valid
        try:
            # Simple date validation
            parts = date.split('/')
            if len(parts) == 3:
                month, day, year = parts
                if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                    return 0.9
        except:
            pass
        
        return 0.5


# For async compatibility
import asyncio