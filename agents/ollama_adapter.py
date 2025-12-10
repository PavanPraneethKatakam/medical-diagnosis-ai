"""
OllamaAdapter - Optional adapter for local Ollama models

This adapter allows using local Ollama models instead of Flan-T5.
Toggleable via OLLAMA_ENABLED environment variable.
"""

import os
import requests
import json
from typing import Optional, Dict


class OllamaAdapter:
    """
    Adapter for calling local Ollama API.
    
    Provides same interface as DecisionMakingAgent for drop-in replacement.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama2",
        enabled: bool = True
    ):
        """
        Initialize Ollama adapter.
        
        Args:
            base_url: Ollama API base URL
            model_name: Model name to use (e.g., "llama2", "mistral", "llama3.2")
            enabled: Whether to enable Ollama (default: True)
        """
        self.base_url = base_url
        self.model_name = model_name
        self.enabled = enabled
        
        if self.enabled:
            print(f"Ollama adapter enabled for model: {model_name}")
            # Test connection
            if not self.test_ollama():
                print("WARNING: Ollama connection test failed. Adapter disabled.")
                self.enabled = False
    
    def test_ollama(self) -> bool:
        """
        Test Ollama API health.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            print(f"Ollama health check failed: {e}")
            return False
    
    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        if not self.enabled:
            raise RuntimeError("Ollama is not enabled or unavailable")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7
                    }
                },
                timeout=60  # Increased from 30 to 60 seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                raise RuntimeError(f"Ollama API error: {response.status_code}")
        
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")
    
    def rank_and_explain(
        self,
        patient_summary: str,
        candidates: list,
        dag: dict,
        summaries: list,
        clinician_comment: str = ""
    ) -> Dict:
        """
        Rank candidates using Ollama (same interface as DecisionMakingAgent).
        
        Args:
            patient_summary: Patient history summary
            candidates: List of (disease_code, score) tuples
            dag: DAG from CausalDiscoveryAgent
            summaries: Document summaries
            clinician_comment: Optional clinician input
            
        Returns:
            Dict with predictions, explanation, evidence, dag
        """
        if not self.enabled:
            raise RuntimeError("Ollama is not enabled")
        
        # Build prompt
        candidates_str = ", ".join([f"{code} ({score:.2f})" for code, score in candidates[:5]])
        
        prompt = f"""You are a medical AI assistant. Analyze this patient case and respond in JSON format.

Patient: {patient_summary}
Candidate diseases: {candidates_str}"""
        
        if clinician_comment:
            prompt += f"\nClinician note: {clinician_comment}"
        
        prompt += """

Provide a JSON object with:
- predictions: array of {code, score, rank} for top 3 diseases
- explanation: brief clinical reasoning

JSON:"""
        
        # Generate response
        try:
            generated_text = self.generate(prompt)
            
            # Try to parse JSON
            import re
            match = re.search(r'\{.*\}', generated_text, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
                result["dag"] = dag
                result["fallback"] = False
                return result
        except Exception as e:
            print(f"Ollama parsing failed: {e}")
        
        # Fallback to simple response
        return {
            "predictions": [
                {"code": code, "score": score, "rank": i+1}
                for i, (code, score) in enumerate(candidates[:3])
            ],
            "explanation": "Generated by Ollama (fallback mode)",
            "evidence": [],
            "dag": dag,
            "fallback": True
        }


def get_ollama_adapter() -> Optional[OllamaAdapter]:
    """
    Get Ollama adapter if enabled.
    
    Returns:
        OllamaAdapter instance if enabled and available, None otherwise
    """
    if os.getenv("OLLAMA_ENABLED", "false").lower() == "true":
        adapter = OllamaAdapter()
        if adapter.enabled:
            return adapter
    return None
