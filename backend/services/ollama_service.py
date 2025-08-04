"""
Ollama LLM service for medical text extraction
Uses phi4:14b model for extracting medications and radiation dates
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

import ollama
from ollama import Options

logger = logging.getLogger(__name__)

# Enhanced BT-RADS configuration prompts (from btrads_main_old.py)
BTRADS_CONFIG = {
    # ═══════════════════════════════════════════════════════════════════════════
    # PREREQUISITES: Separate focused extractions (more accurate)
    # ═══════════════════════════════════════════════════════════════════════════
    
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

IMPORTANT: Include the exact sentence(s) from the clinical note that support your determination.

Return JSON in this format:
{
  "steroid_status": "X",
  "steroid_evidence": "Exact sentence from note about steroids, or empty string if none/unknown",
  "avastin_status": "Y",
  "avastin_evidence": "Exact sentence from note about Avastin, or empty string if none/unknown"
}""",
        "output_format": "json", 
        "json_key": "medication_status",
    },
    
    "radiation_date": {
        "system_message": "You are an expert medical data extractor specializing in brain tumor treatment timelines.",
        "instruction": """Find when this patient completed their most recent radiation therapy course.

Look for: radiation therapy completion, end of XRT, chemoradiation finished, last radiation dose.

Be precise about COMPLETION date, not start date.

IMPORTANT: Include the exact sentence from the clinical note that contains the radiation date information.

Return JSON in this format:
{
  "radiation_date": "MM/DD/YYYY" or "unknown",
  "radiation_evidence": "Exact sentence from note about radiation completion, or empty string if unknown"
}""",
        "output_format": "json", 
        "json_key": "radiation_date",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # BT-RADS FLOWCHART NODES: Enhanced with missing information detection
    # ═══════════════════════════════════════════════════════════════════════════

    # Node 1: Suitable Prior
    "suitable_prior": {
        "system_message": "You are a neuroradiology expert applying BT-RADS criteria for brain tumor follow-up.",
        "instruction": """Determine if there is a suitable prior imaging study for BT-RADS comparison.

BT-RADS requires a baseline study for comparison. Look for:
- References to prior MRI scans
- Comparison statements  
- Baseline post-operative imaging
- Previous follow-up studies

If no clear evidence of prior imaging is found, return "unknown".

Return ONLY: {"available": "yes/no/unknown", "reasoning": "brief explanation of prior imaging availability or information limitation"}""",
        "output_format": "json", 
        "json_key": "suitable_prior",
    },

    # Node 2: Imaging Assessment (Enhanced with volume validation)
    "imaging_assessment": {
        "system_message": "You are a neuroradiology expert applying BT-RADS imaging assessment criteria using quantitative volume data.",
        "instruction": """Compare current imaging with prior using BT-RADS criteria and provided volume data.

CRITICAL: Volume Percentage Interpretation:
- NEGATIVE percentage (-X%) = DECREASED volume = IMPROVEMENT
- POSITIVE percentage (+X%) = INCREASED volume = WORSENING  
- Values near 0% (±10%) = STABLE

CLINICAL SIGNIFICANCE RULE: 
- 1 ml absolute change = 1 x 1 x 1 cm = measurable disease
- Changes < 1 ml are NOT clinically significant, even if >10% percentage change
- Always consider both percentage AND absolute volume changes

MIXED PATTERN RULE: When FLAIR and enhancement change in opposite directions, ALWAYS prioritize the enhancement change.

DECISION LOGIC:
- Both decreased (negative %) -> "improved"
- Both stable (±10%) -> "unchanged" 
- Either shows significant increase (>+10% positive) -> "worse"
- Mixed pattern -> Follow enhancement direction

Examples:
- FLAIR -48%, ENH -25% -> "improved" (both decreased)
- FLAIR +9%, ENH +790% -> "worse" (enhancement dominates)
- FLAIR +15%, ENH -5% -> "unchanged" (enhancement priority: -5% = stable)
- Small volume: 0.5 ml change with 50% increase -> "unchanged" (absolute change < 1 ml)

If volume data is missing or unclear, return "unknown".

Return ONLY: {"assessment": "improved/unchanged/worse/unknown", "reasoning": "volume changes with enhancement priority rule applied or data limitation noted"}""",
        "output_format": "json", 
        "json_key": "imaging_assessment",
    },

    # Node 3A: Medication Effects (Enhanced Context)
    "on_medications": {
        "system_message": "You are a neuroradiology expert applying BT-RADS medication effect criteria for improved imaging.",
        "instruction": """For IMPROVED imaging per BT-RADS, determine which medications could explain the improvement.

BT-RADS specifically considers these medication effects:
- **Avastin (bevacizumab)**: Anti-angiogenic therapy can cause rapid improvement in enhancement 
- **Increasing steroids**: Steroid dose increases can reduce edema and mass effect
- **Neither**: No relevant medication effects identified

Check current medication status and recent changes that correlate with imaging timeline.

BT-RADS decision tree:
- If on Avastin -> evaluate response type (Node 3B)
- If increasing steroids -> evaluate steroid effect timing
- If neither -> true tumor improvement (BT-1a)

If medication status cannot be determined, return "unknown".

Return ONLY: {"on_medications": "avastin/increasing_steroids/neither/unknown", "reasoning": "medication status and temporal correlation with improvement or information limitation"}""",
        "output_format": "json", 
        "json_key": "on_medications",
    },

    # Node 3B: Avastin Response Analysis
    "avastin_response": {
        "system_message": "You are a neuroradiology expert applying BT-RADS Avastin response criteria using volume patterns.",
        "instruction": """For patients on Avastin with improved imaging, determine BT-RADS response type.

BT-RADS Avastin criteria:
- **First study on Avastin with ONLY enhancement improved**: "first_study_enh_only" -> BT-1b
- **Sustained improvement (>1 month) with comprehensive response**: "sustained_improvement" -> BT-1a

Key factors:
1. Is this the first imaging after starting Avastin?
2. Did ONLY enhancement improve while FLAIR stable/worse?
3. Is there sustained improvement over >1 month?

Avastin typically causes rapid enhancement reduction but may not immediately affect FLAIR.

If insufficient information to determine response type, return "unknown".

Return ONLY: {"response_type": "first_study_enh_only/sustained_improvement/unknown", "reasoning": "Avastin timeline and volume pattern analysis per BT-RADS or information limitation"}""",
        "output_format": "json", 
        "json_key": "avastin_response",
    },

    # Node 3C: Steroid Effects
    "steroid_effects": {
        "system_message": "You are a neuroradiology expert applying BT-RADS steroid effect criteria.",
        "instruction": """For improved imaging, determine if increasing steroids explain the improvement per BT-RADS.

BT-RADS steroid criteria:
- Recent steroid dose increase that temporally correlates with imaging improvement
- Steroids can reduce edema, mass effect, and FLAIR signal abnormality

Timeline analysis:
- When were steroids increased?
- Does improvement timing match steroid escalation?
- Is there clinical correlation?

If insufficient information about steroid timing, return "unknown".

Return ONLY: {"steroid_effect": "likely_steroid_effect/unlikely_steroid_effect/unknown", "reasoning": "steroid timing correlation with imaging improvement or information limitation"}""",
        "output_format": "json", 
        "json_key": "steroid_effects",
    },

    # Node 4: Time Since Radiation (Critical 90-day rule)
    "time_since_xrt": {
        "system_message": "You are a neuroradiology expert applying the BT-RADS 90-day radiation rule.",
        "instruction": """For worsening imaging, apply BT-RADS timing criteria relative to radiation completion.

BT-RADS 90-day rule (CRITICAL):
- **<90 days since radiation completion**: "within_90_days" -> BT-3a (Favor treatment effect)
- **≥90 days since radiation completion**: "beyond_90_days" -> Continue algorithm

The 90-day cutoff is evidence-based for distinguishing radiation effects from tumor progression.

Time calculation: Follow-up imaging date - Radiation completion date
Use the calculated days provided in context.

If radiation completion date is unknown, return "unknown".

Return ONLY: {"timing": "within_90_days/beyond_90_days/unknown", "reasoning": "days since radiation completion per BT-RADS 90-day rule or missing radiation date"}""",
        "output_format": "json", 
        "json_key": "time_since_xrt",
    }
}


class OllamaExtractionService:
    """Service for extracting medical information using Ollama LLM"""
    
    def __init__(self, model: str = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "phi4:14b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "300"))
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
            
            # Call Ollama with timeout
            response = await self._call_ollama_with_timeout(messages, output_format="json")
            
            # Parse response
            result = self._parse_medication_response(response)
            
            # Create evidence from LLM's extracted sentences with position tracking
            evidence = []
            
            # Add steroid evidence if provided
            if result.get("steroid_evidence"):
                position = self._find_text_position(result["steroid_evidence"], clinical_note)
                evidence.append({
                    "type": "steroid",
                    "category": "medication",
                    "text": result["steroid_evidence"],
                    "source_type": "llm_extraction",
                    "confidence": 0.95,
                    "relevance_score": 1.0,
                    "llm_extracted": True,
                    "start_pos": position["start"],
                    "end_pos": position["end"],
                    "position_found": position["found"]
                })
            
            # Add avastin evidence if provided
            if result.get("avastin_evidence"):
                position = self._find_text_position(result["avastin_evidence"], clinical_note)
                evidence.append({
                    "type": "avastin",
                    "category": "medication",
                    "text": result["avastin_evidence"],
                    "source_type": "llm_extraction",
                    "confidence": 0.95,
                    "relevance_score": 1.0,
                    "llm_extracted": True,
                    "start_pos": position["start"],
                    "end_pos": position["end"],
                    "position_found": position["found"]
                })
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "data": {
                    "steroid_status": result.get("steroid_status", "unknown"),
                    "avastin_status": result.get("avastin_status", "unknown")
                },
                "evidence": evidence,
                "confidence": self._calculate_confidence(result),
                "processing_time": processing_time,
                "method": "llm",
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Error extracting medications: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0.0
            return {
                "data": {"steroid_status": "unknown", "avastin_status": "unknown"},
                "evidence": [],
                "confidence": 0.0,
                "processing_time": processing_time,
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
            
            # Call Ollama with timeout
            response = await self._call_ollama_with_timeout(messages, output_format="json")
            
            # Parse response
            result = self._parse_radiation_response(response)
            
            # Create evidence from LLM's extracted sentence with position tracking
            evidence = []
            
            if result.get("radiation_evidence"):
                position = self._find_text_position(result["radiation_evidence"], clinical_note)
                evidence.append({
                    "type": "radiation_date",
                    "category": "temporal",
                    "text": result["radiation_evidence"],
                    "date_found": result.get("radiation_date"),
                    "source_type": "llm_extraction",
                    "confidence": 0.95,
                    "relevance_score": 1.0,
                    "llm_extracted": True,
                    "start_pos": position["start"],
                    "end_pos": position["end"],
                    "position_found": position["found"]
                })
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "data": {
                    "radiation_date": result.get("radiation_date", "unknown")
                },
                "evidence": evidence,
                "confidence": self._calculate_date_confidence(result.get("radiation_date")),
                "processing_time": processing_time,
                "method": "llm",
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Error extracting radiation date: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0.0
            return {
                "data": {"radiation_date": "unknown"},
                "evidence": [],
                "confidence": 0.0,
                "processing_time": processing_time,
                "error": str(e),
                "method": "llm",
                "model": self.model
            }
    
    async def extract_btrads_node(self, clinical_note: str, node_name: str, 
                                  context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract information for a specific BT-RADS flowchart node"""
        try:
            start_time = datetime.now()
            
            # Get configuration for the specific node
            if node_name not in BTRADS_CONFIG:
                raise ValueError(f"Unknown BT-RADS node: {node_name}")
            
            config = BTRADS_CONFIG[node_name]
            
            # Build context-aware prompt
            context_str = ""
            if context_data:
                if "volume_data" in context_data:
                    context_str += f"\n\nVOLUME DATA:\n{json.dumps(context_data['volume_data'], indent=2)}"
                if "medication_status" in context_data:
                    context_str += f"\n\nMEDICATION STATUS:\n{json.dumps(context_data['medication_status'], indent=2)}"
                if "radiation_date" in context_data:
                    context_str += f"\n\nRADIATION DATE: {context_data['radiation_date']}"
                if "days_since_radiation" in context_data:
                    context_str += f"\n\nDAYS SINCE RADIATION: {context_data['days_since_radiation']}"
            
            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": config["system_message"]
                },
                {
                    "role": "user",
                    "content": f"{config['instruction']}{context_str}\n\nCLINICAL NOTE:\n{clinical_note}"
                }
            ]
            
            # Call Ollama with timeout
            response = await self._call_ollama_with_timeout(messages, output_format=config.get("output_format", "json"))
            
            # Parse response based on node type
            result = self._parse_node_response(response, node_name)
            
            # Extract evidence based on node type
            evidence = self._extract_node_evidence(clinical_note, node_name, result)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "data": result,
                "evidence": evidence,
                "confidence": self._calculate_node_confidence(node_name, result),
                "processing_time": processing_time,
                "method": "llm",
                "model": self.model,
                "node": node_name
            }
            
        except Exception as e:
            logger.error(f"Error extracting BT-RADS node {node_name}: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0.0
            return {
                "data": {"error": str(e)},
                "evidence": [],
                "confidence": 0.0,
                "processing_time": processing_time,
                "error": str(e),
                "method": "llm",
                "model": self.model,
                "node": node_name
            }
    
    async def _call_ollama_with_timeout(self, messages: List[Dict], output_format: str = None) -> str:
        """Call Ollama with timeout wrapper"""
        import asyncio
        
        try:
            return await asyncio.wait_for(
                self._call_ollama(messages, output_format),
                timeout=float(self.timeout)
            )
        except asyncio.TimeoutError:
            logger.error(f"Ollama timeout after {self.timeout} seconds")
            raise TimeoutError(f"Ollama did not respond within {self.timeout} seconds")
    
    async def _call_ollama(self, messages: List[Dict], output_format: str = None) -> str:
        """Call Ollama API - simple sequential approach"""
        import asyncio
        
        options = {
            "temperature": 0.1,  # Low temperature for consistency
            "top_k": 40,
            "top_p": 0.95,
            "num_ctx": 16000,  # Larger context for phi4:14b like in old implementation
            "num_predict": 512,  # Standard output length
            "repeat_penalty": 1.1,
            "seed": 42,
            "num_thread": 8,  # Use more threads for faster processing
        }
        
        try:
            # Simple synchronous call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=self.model,
                    messages=messages,
                    format="json" if output_format == "json" else None,
                    options=options,
                    keep_alive="10m"
                )
            )
            
            content = response.get("message", {}).get("content", "")
            if not content.strip():
                raise ValueError("Empty response from Ollama")
            
            return content
            
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise
    
    def _parse_medication_response(self, response: str) -> Dict[str, str]:
        """Parse medication extraction response with fallback handling"""
        try:
            # Try direct JSON parsing
            data = json.loads(response)
            
            # Handle nested structure
            if "medication_status" in data and isinstance(data["medication_status"], dict):
                return data["medication_status"]
            
            # Direct structure with evidence
            return {
                "steroid_status": data.get("steroid_status", "unknown"),
                "steroid_evidence": data.get("steroid_evidence", ""),
                "avastin_status": data.get("avastin_status", "unknown"),
                "avastin_evidence": data.get("avastin_evidence", "")
            }
            
        except json.JSONDecodeError:
            # Fallback: Extract from text
            result = {
                "steroid_status": "unknown", 
                "avastin_status": "unknown",
                "steroid_evidence": "",
                "avastin_evidence": ""
            }
            
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
            return {
                "radiation_date": data.get("radiation_date", "unknown"),
                "radiation_evidence": data.get("radiation_evidence", "")
            }
            
        except json.JSONDecodeError:
            # Fallback: Extract date using regex
            result = {"radiation_date": "unknown", "radiation_evidence": ""}
            
            date_match = re.search(r'"radiation_date":\s*"([^"]+)"', response)
            if date_match:
                result["radiation_date"] = date_match.group(1)
            else:
                # Try to find date pattern
                date_pattern = re.search(r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b', response)
                if date_pattern:
                    result["radiation_date"] = date_pattern.group(1)
            
            return result
    
    def _extract_medication_evidence(self, text: str, result: Dict[str, str]) -> List[Dict]:
        """Extract detailed evidence snippets for medication findings with enhanced context"""
        evidence = []
        
        # Enhanced search patterns with more specific medication mentions
        steroid_patterns = [
            (r'(?i)(dexamethasone|decadron)\s*(\d+\s*mg)', 'specific_dose'),
            (r'(?i)(steroid|prednis\w+)\s+(?:dose|dosage)\s*(?:of\s*)?(\d+\s*mg)', 'dose_mention'),
            (r'(?i)(?:increase|escalat\w+)\s+(?:in\s+)?(?:steroid|dexamethasone|decadron)', 'dose_increase'),
            (r'(?i)(?:decrease|taper|reduc\w+)\s+(?:in\s+)?(?:steroid|dexamethasone|decadron)', 'dose_decrease'),
            (r'(?i)(?:start\w+|initiat\w+)\s+(?:on\s+)?(?:steroid|dexamethasone|decadron)', 'started'),
            (r'(?i)(?:continu\w+|maintain\w+)\s+(?:on\s+)?(?:steroid|dexamethasone|decadron)', 'stable'),
            (r'(?i)no\s+(?:steroid|dexamethasone|decadron)', 'none'),
        ]
        
        avastin_patterns = [
            (r'(?i)(avastin|bevacizumab)\s*(?:infusion|dose|treatment)', 'treatment_mention'),
            (r'(?i)first\s+(?:dose|infusion|treatment)\s+(?:of\s+)?(?:avastin|bevacizumab)', 'first_treatment'),
            (r'(?i)(?:continue|ongoing)\s+(?:avastin|bevacizumab)', 'ongoing'),
            (r'(?i)(?:start\w+|initiat\w+)\s+(?:on\s+)?(?:avastin|bevacizumab)', 'started'),
            (r'(?i)(?:avastin|bevacizumab)\s+(?:cycle|infusion)\s*#?\s*\d+', 'cycle_number'),
            (r'(?i)anti-?angiogenic\s+(?:therapy|treatment)', 'anti_angiogenic'),
            (r'(?i)no\s+(?:avastin|bevacizumab|anti-?angiogenic)', 'none'),
        ]
        
        # Extract steroid evidence with enhanced context
        for pattern, pattern_type in steroid_patterns:
            for match in re.finditer(pattern, text):
                # Get broader context (150 chars before/after)
                context_start = max(0, match.start() - 150)
                context_end = min(len(text), match.end() + 150)
                context = text[context_start:context_end]
                
                # Find sentence boundaries for better context
                sentence_start = text.rfind('.', context_start, match.start())
                sentence_start = sentence_start + 1 if sentence_start != -1 else context_start
                sentence_end = text.find('.', match.end(), context_end)
                sentence_end = sentence_end if sentence_end != -1 else context_end
                
                evidence.append({
                    "type": "steroid",
                    "category": "medication",
                    "text": text[sentence_start:sentence_end].strip(),
                    "matched_text": match.group(0),
                    "pattern": pattern,
                    "pattern_type": pattern_type,
                    "confidence": self._calculate_pattern_confidence(pattern_type, result.get('steroid_status')),
                    "start_pos": match.start(),
                    "end_pos": match.end(),
                    "context_start": sentence_start,
                    "context_end": sentence_end,
                    "relevance_score": 0.9 if pattern_type in ['specific_dose', 'dose_increase', 'dose_decrease'] else 0.7,
                    "source_type": "pattern_match"
                })
        
        # Extract Avastin evidence with enhanced context
        for pattern, pattern_type in avastin_patterns:
            for match in re.finditer(pattern, text):
                # Get broader context
                context_start = max(0, match.start() - 150)
                context_end = min(len(text), match.end() + 150)
                
                # Find sentence boundaries
                sentence_start = text.rfind('.', context_start, match.start())
                sentence_start = sentence_start + 1 if sentence_start != -1 else context_start
                sentence_end = text.find('.', match.end(), context_end)
                sentence_end = sentence_end if sentence_end != -1 else context_end
                
                evidence.append({
                    "type": "avastin",
                    "category": "medication",
                    "text": text[sentence_start:sentence_end].strip(),
                    "matched_text": match.group(0),
                    "pattern": pattern,
                    "pattern_type": pattern_type,
                    "confidence": self._calculate_pattern_confidence(pattern_type, result.get('avastin_status')),
                    "start_pos": match.start(),
                    "end_pos": match.end(),
                    "context_start": sentence_start,
                    "context_end": sentence_end,
                    "relevance_score": 0.95 if pattern_type in ['first_treatment', 'cycle_number'] else 0.8,
                    "source_type": "pattern_match"
                })
        
        # Sort by relevance score and limit to top evidence
        evidence.sort(key=lambda x: x['relevance_score'], reverse=True)
        return evidence[:10]  # Return more evidence for better context
    
    def _calculate_pattern_confidence(self, pattern_type: str, extracted_status: str) -> float:
        """Calculate confidence based on pattern type and extracted status alignment"""
        high_confidence_patterns = {
            'specific_dose': 0.95,
            'dose_increase': 0.9,
            'dose_decrease': 0.9,
            'first_treatment': 0.95,
            'cycle_number': 0.9,
        }
        
        medium_confidence_patterns = {
            'dose_mention': 0.8,
            'started': 0.85,
            'stable': 0.8,
            'ongoing': 0.8,
            'treatment_mention': 0.8,
        }
        
        if pattern_type in high_confidence_patterns:
            return high_confidence_patterns[pattern_type]
        elif pattern_type in medium_confidence_patterns:
            return medium_confidence_patterns[pattern_type]
        else:
            return 0.7
    
    def _extract_radiation_evidence(self, text: str, radiation_date: str) -> List[Dict]:
        """Extract detailed evidence snippets for radiation date with enhanced context"""
        evidence = []
        
        # Enhanced radiation patterns with types
        radiation_patterns = [
            # Date range patterns (capture both start and end)
            (r'(?i)radiation.*?(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:to|-|–)\s*(\d{1,2}/\d{1,2}/\d{2,4})', 'date_range'),
            (r'(?i)(?:xrt|radiotherapy).*?(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:to|-|–)\s*(\d{1,2}/\d{1,2}/\d{2,4})', 'date_range'),
            (r'(?i)from\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*to\s*(\d{1,2}/\d{1,2}/\d{2,4}).*?radiation', 'date_range'),
            
            # Completion patterns
            (r'(?i)radiation.*?(?:complet\w+|finish\w+|end\w+).*?(\d{1,2}/\d{1,2}/\d{2,4})', 'completion'),
            (r'(?i)(?:xrt|rt|radiotherapy).*?(?:complet\w+|finish\w+).*?(\d{1,2}/\d{1,2}/\d{2,4})', 'completion'),
            (r'(?i)(\d{1,2}/\d{1,2}/\d{2,4}).*?radiation.*?(?:complet\w+|finish\w+)', 'completion'),
            
            # Started/ended patterns
            (r'(?i)started\s+radiation.*?(\d{1,2}/\d{1,2}/\d{2,4})', 'started'),
            (r'(?i)last\s+(?:dose|fraction).*?(\d{1,2}/\d{1,2}/\d{2,4})', 'last_dose'),
            (r'(?i)last\s+dose\s+was\s+on\s+(\d{1,2}/\d{1,2}/\d{2,4})', 'last_dose'),
            (r'(?i)(?:concurrent|adjuvant)\s+(?:chemo)?radiation.*?(\d{1,2}/\d{1,2}/\d{2,4})', 'chemoradiation'),
            
            # General radiation mentions
            (r'(?i)(radiation|xrt|radiotherapy|rt\b)', 'mention'),
            (r'(?i)no\s+(?:prior\s+)?radiation', 'no_radiation'),
            (r'(?i)radiation\s+naive', 'no_radiation'),
        ]
        
        for pattern, pattern_type in radiation_patterns:
            for match in re.finditer(pattern, text):
                # Get broader context
                context_start = max(0, match.start() - 150)
                context_end = min(len(text), match.end() + 150)
                
                # Find sentence boundaries
                sentence_start = text.rfind('.', context_start, match.start())
                sentence_start = sentence_start + 1 if sentence_start != -1 else context_start
                sentence_end = text.find('.', match.end(), context_end)
                sentence_end = sentence_end if sentence_end != -1 else context_end
                
                # Extract dates based on pattern type
                date_found = None
                if pattern_type == 'date_range' and len(match.groups()) >= 2:
                    # For date ranges, use the end date
                    date_found = match.group(2)
                elif match.groups() and pattern_type in ['completion', 'last_dose', 'started', 'chemoradiation']:
                    date_found = match.group(1)
                
                # Calculate relevance based on pattern type
                relevance_map = {
                    'completion': 0.95,
                    'last_dose': 0.9,
                    'date_range': 0.9,
                    'chemoradiation': 0.85,
                    'started': 0.7,  # Start date is less relevant than end date
                    'mention': 0.5,
                    'no_radiation': 0.8,
                }
                
                evidence.append({
                    "type": "radiation_date",
                    "category": "temporal",
                    "text": text[sentence_start:sentence_end].strip(),
                    "matched_text": match.group(0),
                    "date_found": date_found,
                    "pattern": pattern,
                    "pattern_type": pattern_type,
                    "confidence": self._calculate_date_pattern_confidence(pattern_type, date_found, radiation_date),
                    "start_pos": match.start(),
                    "end_pos": match.end(),
                    "context_start": sentence_start,
                    "context_end": sentence_end,
                    "relevance_score": relevance_map.get(pattern_type, 0.5),
                    "source_type": "pattern_match"
                })
        
        # Sort by relevance score
        evidence.sort(key=lambda x: x['relevance_score'], reverse=True)
        return evidence[:10]  # Return more evidence for better context
    
    def _calculate_date_pattern_confidence(self, pattern_type: str, found_date: str, extracted_date: str) -> float:
        """Calculate confidence based on pattern type and date matching"""
        if pattern_type in ['completion', 'last_dose', 'date_range']:
            base_confidence = 0.9
        elif pattern_type in ['chemoradiation', 'started']:
            base_confidence = 0.8
        elif pattern_type == 'no_radiation':
            base_confidence = 0.85
        else:
            base_confidence = 0.6
        
        # Boost confidence if found date matches extracted date
        if found_date and extracted_date and found_date == extracted_date:
            base_confidence = min(1.0, base_confidence + 0.1)
        
        return base_confidence
    
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
    
    def _find_text_position(self, text: str, full_text: str) -> Dict[str, Any]:
        """Find the position of extracted text within the full clinical note
        
        Args:
            text: The extracted text to find
            full_text: The full clinical note to search in
            
        Returns:
            Dict with start, end positions and found flag
        """
        if not text or not full_text:
            return {"start": 0, "end": 0, "found": False}
        
        # Strategy 1: Try exact match
        start_pos = full_text.find(text)
        if start_pos != -1:
            return {
                "start": start_pos,
                "end": start_pos + len(text),
                "found": True
            }
        
        # Strategy 2: Case-insensitive match
        lower_full = full_text.lower()
        lower_text = text.lower()
        start_pos = lower_full.find(lower_text)
        if start_pos != -1:
            return {
                "start": start_pos,
                "end": start_pos + len(text),
                "found": True
            }
        
        # Strategy 3: Normalized whitespace match
        # Normalize whitespace in both texts
        norm_full = ' '.join(full_text.split())
        norm_text = ' '.join(text.split())
        
        # Find in normalized version
        norm_start = norm_full.find(norm_text)
        if norm_start != -1:
            # Map back to original position (approximate)
            # Count characters in original up to the normalized position
            char_count = 0
            norm_count = 0
            original_start = 0
            
            for i, char in enumerate(full_text):
                if norm_count >= norm_start:
                    original_start = i
                    break
                    
                if char.isspace():
                    # In normalized, multiple spaces become one
                    if i == 0 or not full_text[i-1].isspace():
                        norm_count += 1
                else:
                    norm_count += 1
            
            return {
                "start": original_start,
                "end": min(original_start + len(text), len(full_text)),
                "found": True
            }
        
        # Strategy 4: Try to find a significant substring (first 50 chars)
        if len(text) > 50:
            substring = text[:50]
            start_pos = full_text.find(substring)
            if start_pos != -1:
                return {
                    "start": start_pos,
                    "end": min(start_pos + len(text), len(full_text)),
                    "found": True
                }
        
        # Not found
        return {"start": 0, "end": 0, "found": False}
    
    def _parse_node_response(self, response: str, node_name: str) -> Dict[str, Any]:
        """Parse response for specific BT-RADS node"""
        try:
            # Try to parse as JSON
            import json
            # Find JSON boundaries
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except Exception as e:
            logger.warning(f"Failed to parse JSON for node {node_name}: {e}")
        
        # Return default based on node type
        defaults = {
            "suitable_prior": {"available": "unknown", "reasoning": "Failed to parse response"},
            "imaging_assessment": {"assessment": "unknown", "reasoning": "Failed to parse response"},
            "on_medications": {"on_medications": "unknown", "reasoning": "Failed to parse response"},
            "avastin_response": {"response_type": "unknown", "reasoning": "Failed to parse response"},
            "steroid_effects": {"steroid_effect": "unknown", "reasoning": "Failed to parse response"},
            "time_since_xrt": {"timing": "unknown", "reasoning": "Failed to parse response"},
        }
        
        return defaults.get(node_name, {"result": "unknown"})
    
    def _extract_node_evidence(self, text: str, node_name: str, result: Dict[str, Any]) -> List[Dict]:
        """Extract evidence for specific BT-RADS node"""
        evidence = []
        
        # Node-specific evidence patterns
        if node_name == "suitable_prior":
            patterns = [
                (r'(?i)prior\s+(?:mri|scan|imaging|study)', 'prior_mention'),
                (r'(?i)compar\w+\s+(?:to|with)\s+(?:prior|previous)', 'comparison'),
                (r'(?i)baseline\s+(?:mri|scan|imaging)', 'baseline'),
                (r'(?i)no\s+prior\s+(?:mri|scan|imaging)', 'no_prior'),
            ]
            category = "imaging"
        
        elif node_name == "imaging_assessment":
            patterns = [
                (r'(?i)(?:increase|enlarg|progress|worsen)', 'worsening'),
                (r'(?i)(?:decrease|improv|regress|shrink)', 'improvement'),
                (r'(?i)(?:stable|unchanged|no\s+change)', 'stable'),
                (r'(?i)(?:flair|t2)\s+(?:signal|hyperintensity)', 'flair_mention'),
                (r'(?i)(?:enhancement|contrast|gadolinium)', 'enhancement_mention'),
            ]
            category = "imaging"
        
        elif node_name == "on_medications":
            # Reuse medication patterns
            return self._extract_medication_evidence(text, result)
        
        elif node_name == "time_since_xrt":
            # Reuse radiation patterns
            return self._extract_radiation_evidence(text, result.get("radiation_date", ""))
        
        else:
            # Generic patterns for other nodes
            patterns = []
            category = "clinical"
        
        # Extract evidence based on patterns
        for pattern, pattern_type in patterns:
            for match in re.finditer(pattern, text):
                # Get sentence context
                sentence_start = text.rfind('.', max(0, match.start() - 150), match.start())
                sentence_start = sentence_start + 1 if sentence_start != -1 else max(0, match.start() - 150)
                sentence_end = text.find('.', match.end(), min(len(text), match.end() + 150))
                sentence_end = sentence_end if sentence_end != -1 else min(len(text), match.end() + 150)
                
                evidence.append({
                    "type": node_name,
                    "category": category,
                    "text": text[sentence_start:sentence_end].strip(),
                    "matched_text": match.group(0),
                    "pattern": pattern,
                    "pattern_type": pattern_type,
                    "confidence": 0.8,
                    "start_pos": match.start(),
                    "end_pos": match.end(),
                    "context_start": sentence_start,
                    "context_end": sentence_end,
                    "relevance_score": 0.8,
                    "source_type": "pattern_match"
                })
        
        # Sort by relevance and return top evidence
        evidence.sort(key=lambda x: x['relevance_score'], reverse=True)
        return evidence[:10]
    
    def _calculate_node_confidence(self, node_name: str, result: Dict[str, Any]) -> float:
        """Calculate confidence for BT-RADS node extraction"""
        # Check if result contains unknown values
        unknown_count = sum(1 for v in result.values() if isinstance(v, str) and 'unknown' in v.lower())
        
        if unknown_count == 0:
            return 0.9
        elif unknown_count == 1:
            return 0.6
        else:
            return 0.3


# For async compatibility
import asyncio