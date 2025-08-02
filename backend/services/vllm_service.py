"""
vLLM Service for high-performance LLM inference
Supports Llama 3.1, Mixtral, and other open models
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class VLLMConfig(BaseModel):
    """Configuration for vLLM service"""
    base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    timeout: int = 120
    max_retries: int = 3
    models: Dict[str, Dict[str, Any]] = {
        "llama3.1-70b": {
            "model_name": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "max_tokens": 2048,
            "temperature": 0.1,
            "top_p": 0.95,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "quantization": "AWQ",  # 4-bit quantization for efficiency
        },
        "mixtral-8x7b": {
            "model_name": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "max_tokens": 1024,
            "temperature": 0.1,
            "top_p": 0.95,
            "quantization": "GPTQ",
        },
        "biomistral-7b": {
            "model_name": "BioMistral/BioMistral-7B",
            "max_tokens": 1024,
            "temperature": 0.1,
            "top_p": 0.95,
        }
    }

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class CompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: bool = False
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    response_format: Optional[Dict[str, str]] = None

class VLLMService:
    """Service for interacting with vLLM server"""
    
    def __init__(self, config: Optional[VLLMConfig] = None):
        self.config = config or VLLMConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self._model_cache = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self._check_health()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _check_health(self):
        """Check if vLLM server is healthy"""
        try:
            async with self.session.get(
                f"{self.config.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"vLLM server unhealthy: {response.status}")
                logger.info("vLLM server is healthy")
        except Exception as e:
            logger.error(f"Failed to connect to vLLM server: {e}")
            raise RuntimeError(
                f"Cannot connect to vLLM server at {self.config.base_url}. "
                "Please ensure vLLM is running with: "
                "python -m vllm.entrypoints.openai.api_server --model meta-llama/Meta-Llama-3.1-70B-Instruct"
            )
    
    async def list_models(self) -> List[str]:
        """List available models on vLLM server"""
        try:
            async with self.session.get(
                f"{self.config.base_url}/v1/models"
            ) as response:
                data = await response.json()
                return [model["id"] for model in data.get("data", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return list(self.config.models.keys())
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama3.1-70b",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Get chat completion from vLLM"""
        
        # Get model config
        model_config = self.config.models.get(model, self.config.models["llama3.1-70b"])
        
        # Build request
        request = CompletionRequest(
            model=model_config["model_name"],
            messages=[ChatMessage(**msg) for msg in messages],
            temperature=temperature or model_config.get("temperature", 0.1),
            max_tokens=max_tokens or model_config.get("max_tokens", 1024),
            top_p=model_config.get("top_p", 0.95),
            presence_penalty=model_config.get("presence_penalty", 0.0),
            frequency_penalty=model_config.get("frequency_penalty", 0.0),
            stream=stream,
            response_format=response_format
        )
        
        # Retry logic
        for attempt in range(self.config.max_retries):
            try:
                return await self._make_request(request)
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
    
    async def _make_request(self, request: CompletionRequest) -> Dict[str, Any]:
        """Make request to vLLM server"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        async with self.session.post(
            f"{self.config.base_url}/v1/chat/completions",
            json=request.dict(exclude_none=True),
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"vLLM request failed: {response.status} - {error_text}")
            
            return await response.json()
    
    def select_model_for_task(self, task_type: str, complexity: str = "medium") -> str:
        """Select appropriate model based on task type and complexity"""
        
        model_selection = {
            # High complexity tasks - use Llama 3.1 70B
            ("extraction", "high"): "llama3.1-70b",
            ("reasoning", "high"): "llama3.1-70b",
            ("medical_analysis", "high"): "llama3.1-70b",
            
            # Medium complexity - use Mixtral
            ("extraction", "medium"): "mixtral-8x7b",
            ("reasoning", "medium"): "mixtral-8x7b",
            ("medical_analysis", "medium"): "biomistral-7b",
            
            # Low complexity - use smaller models
            ("extraction", "low"): "biomistral-7b",
            ("reasoning", "low"): "mixtral-8x7b",
            ("medical_analysis", "low"): "biomistral-7b",
        }
        
        return model_selection.get((task_type, complexity), "mixtral-8x7b")
    
    async def extract_btrads_info(
        self,
        clinical_note: str,
        extraction_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract BT-RADS specific information"""
        
        # Determine complexity based on extraction type
        complexity_map = {
            "prior_assessment": "low",
            "imaging_comparison": "high",
            "medication_status": "medium",
            "radiation_timeline": "medium",
            "component_analysis": "high",
            "extent_analysis": "high",
            "progression_pattern": "high"
        }
        
        complexity = complexity_map.get(extraction_type, "medium")
        model = self.select_model_for_task("medical_analysis", complexity)
        
        # Build specialized prompt based on extraction type
        system_prompt = self._get_system_prompt(extraction_type)
        user_prompt = self._build_extraction_prompt(clinical_note, extraction_type, context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Request JSON output for structured extraction
        response_format = {"type": "json_object"} if extraction_type != "reasoning" else None
        
        start_time = datetime.now()
        response = await self.chat_completion(
            messages=messages,
            model=model,
            response_format=response_format,
            temperature=0.1  # Low temperature for consistency
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Parse response
        content = response["choices"][0]["message"]["content"]
        
        try:
            if response_format:
                extracted_data = json.loads(content)
            else:
                extracted_data = {"text": content}
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {content}")
            extracted_data = {"error": "Failed to parse response", "raw": content}
        
        return {
            "data": extracted_data,
            "model": model,
            "processing_time": processing_time,
            "usage": response.get("usage", {}),
            "extraction_type": extraction_type
        }
    
    def _get_system_prompt(self, extraction_type: str) -> str:
        """Get system prompt for specific extraction type"""
        
        prompts = {
            "prior_assessment": """You are an expert radiologist specializing in brain tumor imaging assessment. 
Your task is to determine if suitable prior imaging exists for comparison.
Focus on identifying mentions of previous MRI, CT scans, or other brain imaging studies.
Be precise about dates and imaging modalities.""",
            
            "imaging_comparison": """You are an expert neuroradiologist analyzing brain tumor progression.
Your task is to compare current imaging with prior studies and assess volume changes.
Focus on FLAIR and enhancement changes, using precise medical terminology.
Consider the enhancement priority rule when FLAIR and enhancement show different patterns.""",
            
            "medication_status": """You are a neuro-oncology pharmacist specializing in brain tumor treatments.
Your task is to extract current medication status, focusing on steroids and Avastin.
Distinguish between stable, increasing, decreasing doses and new medications.
Be precise about medication names, doses, and changes.""",
            
            "radiation_timeline": """You are a radiation oncologist tracking treatment timelines.
Your task is to identify radiation therapy completion dates.
Focus on finding the END date of radiation, not the start date.
Look for terms like 'completed XRT', 'finished radiation', 'last fraction'.""",
            
            "component_analysis": """You are a neuroradiologist analyzing tumor component changes.
Your task is to determine whether changes are primarily in FLAIR or enhancement.
Apply the 40% rule for significant changes.
Consider mixed patterns and apply enhancement priority when applicable.""",
            
            "extent_analysis": """You are a neuroradiologist assessing disease extent.
Your task is to evaluate the spatial distribution of changes.
Distinguish between local progression, distant progression, and multifocal disease.
Consider both FLAIR and enhancement patterns.""",
            
            "progression_pattern": """You are a neuro-oncology expert evaluating progression patterns.
Your task is to synthesize all findings and determine the progression pattern.
Consider treatment effects, pseudoprogression, and true progression.
Apply BT-RADS criteria for final classification."""
        }
        
        return prompts.get(extraction_type, prompts["prior_assessment"])
    
    def _build_extraction_prompt(
        self,
        clinical_note: str,
        extraction_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build extraction prompt with context"""
        
        context_str = ""
        if context:
            context_str = f"\n\nAdditional Context:\n"
            if "baseline_date" in context:
                context_str += f"- Baseline scan date: {context['baseline_date']}\n"
            if "followup_date" in context:
                context_str += f"- Current scan date: {context['followup_date']}\n"
            if "flair_change_pct" in context:
                context_str += f"- FLAIR volume change: {context['flair_change_pct']:.1f}%\n"
            if "enhancement_change_pct" in context:
                context_str += f"- Enhancement volume change: {context['enhancement_change_pct']:.1f}%\n"
        
        # Build specific extraction instructions
        extraction_instructions = self._get_extraction_instructions(extraction_type)
        
        return f"""Clinical Note:
{clinical_note}
{context_str}
{extraction_instructions}"""
    
    def _get_extraction_instructions(self, extraction_type: str) -> str:
        """Get specific extraction instructions"""
        
        instructions = {
            "prior_assessment": """
Extract the following information and return as JSON:
{
    "has_suitable_prior": true/false,
    "prior_date": "YYYY-MM-DD or null",
    "prior_modality": "MRI/CT/null",
    "days_between_scans": number or null,
    "confidence": 0.0-1.0,
    "evidence": ["relevant quotes from the note"]
}""",
            
            "medication_status": """
Extract the following information and return as JSON:
{
    "steroid_status": "none/stable/increasing/decreasing/started/unknown",
    "steroid_details": "medication name and dose if available",
    "avastin_status": "none/ongoing/first_treatment/started/unknown",
    "avastin_details": "cycle number or dose if available",
    "confidence": 0.0-1.0,
    "evidence": ["relevant quotes from the note"]
}""",
            
            "imaging_comparison": """
Analyze the imaging changes and return as JSON:
{
    "overall_assessment": "improved/stable/worse",
    "flair_assessment": "increased/stable/decreased",
    "enhancement_assessment": "increased/stable/decreased", 
    "mixed_pattern": true/false,
    "enhancement_priority_applied": true/false,
    "confidence": 0.0-1.0,
    "evidence": ["relevant quotes from the note"]
}"""
        }
        
        return instructions.get(extraction_type, "Extract relevant information from the clinical note.")


# Singleton instance for easy import
vllm_service = None

async def get_vllm_service() -> VLLMService:
    """Get or create vLLM service instance"""
    global vllm_service
    if vllm_service is None:
        vllm_service = VLLMService()
        await vllm_service.__aenter__()
    return vllm_service