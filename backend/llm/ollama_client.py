"""
Ollama LLM client with retry logic and model management
"""
import time
from typing import List, Dict, Optional, Any
import ollama
from ollama import Options


class OllamaClient:
    """Wrapper for Ollama with retry logic and model management"""
    
    def __init__(self, default_model: str = "phi4:14b"):
        self.default_model = default_model
        self.available_models = self._get_available_models()
        
    def _get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            models = ollama.list()["models"]
            return [m["model"] for m in models]
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def ensure_model_available(self, model: str) -> bool:
        """Ensure model is available, pull if necessary"""
        if model in self.available_models:
            return True
            
        try:
            print(f"Pulling model {model}...")
            ollama.pull(model)
            self.available_models = self._get_available_models()
            return model in self.available_models
        except Exception as e:
            print(f"Error pulling model {model}: {e}")
            return False
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        output_format: str = "text",
        temperature: float = 0.0,
        top_k: int = 40,
        top_p: float = 0.95,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> Optional[str]:
        """
        Chat with Ollama model with retry logic
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            output_format: 'text' or 'json'
            temperature: Temperature for sampling (0.0 = deterministic)
            top_k: Top K tokens to consider
            top_p: Top P (nucleus) sampling
            max_retries: Number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Response content or None if failed
        """
        model = model or self.default_model
        
        # Ensure model is available
        if not self.ensure_model_available(model):
            print(f"Model {model} not available and couldn't be pulled")
            return None
        
        options = Options(
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            num_ctx=16_000,  # Context window
            num_predict=512,  # Max tokens to generate
        )
        
        for attempt in range(max_retries):
            try:
                response = ollama.chat(
                    model=model,
                    format="json" if output_format == "json" else None,
                    keep_alive="10m",  # Keep model loaded for 10 minutes
                    options=options,
                    messages=messages,
                )
                
                content = response.get("message", {}).get("content", "")
                if not content.strip():
                    raise ValueError("Empty response content")
                    
                return content
                
            except Exception as e:
                print(f"LLM attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
        return None
    
    def extract_with_prompt(
        self,
        prompt_config: Dict[str, Any],
        context: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Extract information using a prompt configuration
        
        Args:
            prompt_config: Configuration with 'system_message', 'instruction', 'output_format'
            context: Clinical note context to analyze
            model: Model to use
            **kwargs: Additional chat parameters
            
        Returns:
            Extracted content or None
        """
        messages = [
            {
                "role": "system",
                "content": prompt_config.get("system_message", "You are a medical data extractor.")
            },
            {
                "role": "user",
                "content": f"{context}\n\nTASK: {prompt_config.get('instruction', '')}"
            }
        ]
        
        # Add few-shot examples if provided
        if "few_shots" in prompt_config:
            messages = [messages[0]] + prompt_config["few_shots"] + [messages[1]]
        
        return self.chat(
            messages=messages,
            model=model,
            output_format=prompt_config.get("output_format", "text"),
            **kwargs
        )


# Singleton instance
_ollama_client = None

def get_ollama_client() -> OllamaClient:
    """Get or create the Ollama client singleton"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client