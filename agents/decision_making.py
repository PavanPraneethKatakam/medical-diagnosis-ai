"""
DecisionMakingAgent - Ranks predictions and generates explanations using SLM

This agent uses Flan-T5 to rank disease predictions and generate explanations,
with deterministic fallback logic for robustness.
"""

import json
import re
from typing import List, Dict, Tuple, Optional, Generator
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import numpy as np
from .model_pool import get_model_pool


class DecisionMakingAgent:
    """
    Agent for ranking disease predictions and generating explanations.
    
    Uses Flan-T5 with deterministic fallback for robustness.
    """
    
    def __init__(self, model_name: str = "google/flan-t5-base", device: str = "cpu"):
        """
        Initialize the Decision Making Agent.
        
        Args:
            model_name: HuggingFace model name
            device: Device to run model on ("cpu" or "cuda")
        """
        self.model_name = model_name
        self.device = device
        
        # Use model pool singleton
        model_pool = get_model_pool()
        self.tokenizer, self.model, self.device = model_pool.load_slm_model(model_name)
    
    def rank_and_explain(
        self,
        patient_summary: str,
        candidates: List[Tuple[str, float]],
        dag: Dict,
        summaries: List[Dict],
        clinician_comment: str = ""
    ) -> Dict:
        """
        Rank candidates and generate explanation.
        
        Args:
            patient_summary: Summary of patient history
            candidates: List of (disease_code, transition_score) tuples
            dag: DAG from CausalDiscoveryAgent
            summaries: Document summaries from KnowledgeSynthesisAgent
            clinician_comment: Optional clinician input
            
        Returns:
            Dict with predictions, explanation, evidence, dag
        """
        if not candidates:
            return {
                "predictions": [],
                "explanation": "No candidate diseases identified.",
                "evidence": [],
                "dag": dag,
                "fallback": False
            }
        
        # Build prompt for Flan-T5
        prompt = self._build_prompt(
            patient_summary, candidates, dag, summaries, clinician_comment
        )
        
        # Try to get structured JSON from model
        try:
            model_output = self._generate_from_model(prompt)
            result = self._parse_model_output(model_output)
            
            if result:
                # Successfully parsed JSON from model
                result["dag"] = dag
                result["fallback"] = False
                return result
        except Exception as e:
            print(f"Model generation failed: {e}")
        
        # Fallback to deterministic ranking
        print("Using deterministic fallback ranking...")
        return self._deterministic_fallback(
            patient_summary, candidates, dag, summaries, clinician_comment
        )
    
    def _build_prompt(
        self,
        patient_summary: str,
        candidates: List[Tuple[str, float]],
        dag: Dict,
        summaries: List[Dict],
        clinician_comment: str
    ) -> str:
        """Build prompt for Flan-T5 with strict JSON enforcement."""
        # Format candidates
        candidates_str = ", ".join([f"{code} ({score:.2f})" for code, score in candidates[:5]])
        
        # Format top evidence
        evidence_str = ""
        if summaries:
            top_summaries = summaries[:3]
            evidence_str = " ".join([
                f"{s['disease_code']}: {s['summary'][:100]}"
                for s in top_summaries
            ])
        
        prompt = f"""You are a medical AI assistant. 

CRITICAL: Respond with STRICT JSON ONLY. No extra text before or after JSON.

Patient: {patient_summary}
Candidate diseases: {candidates_str}
Medical evidence: {evidence_str}"""
        
        if clinician_comment:
            prompt += f"\nClinician note: {clinician_comment}"
        
        prompt += """

Output ONLY this JSON structure (no other text):
{
  "predictions": [
    {"code": "DISEASE_CODE", "score": 0.XX, "rank": 1}
  ],
  "explanation": "Brief clinical reasoning in 1-2 sentences",
  "evidence": [
    {"disease_code": "CODE", "snippet": "relevant text"}
  ]
}

IMPORTANT:
- Use double quotes for all strings
- No trailing commas
- Keep explanation under 200 characters
- If uncertain, output valid JSON with empty arrays

JSON:"""
        
        return prompt
    
    def _generate_from_model(self, prompt: str, max_length: int = 300) -> str:
        """Generate text from Flan-T5 model."""
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                num_beams=4,
                early_stopping=True,
                temperature=0.7
            )
        
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return generated_text
    
    def _parse_model_output(self, output: str) -> Optional[Dict]:
        """
        Parse model output as JSON with robust fallback strategies.
        
        Implements 5-stage extraction pipeline:
        1. Direct JSON parse
        2. Extract first {...} block
        3. Extract nested {...} block
        4. Clean invalid tokens and retry
        5. Return None (triggers deterministic fallback)
        
        Args:
            output: Raw model output
            
        Returns:
            Parsed dict or None if all strategies fail
        """
        # Strategy 1: Direct JSON parse
        try:
            result = json.loads(output)
            if self._validate_output(result):
                return result
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract first {...} block (non-nested)
        match = re.search(r'\{[^{}]*\}', output, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                if self._validate_output(result):
                    return result
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Extract nested {...} block (greedy)
        match = re.search(r'\{.*\}', output, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                if self._validate_output(result):
                    return result
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Clean invalid tokens and retry
        cleaned = self._clean_invalid_tokens(output)
        if cleaned != output:
            try:
                result = json.loads(cleaned)
                if self._validate_output(result):
                    return result
            except json.JSONDecodeError:
                pass
            
            # Try extracting from cleaned output
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(0))
                    if self._validate_output(result):
                        return result
                except json.JSONDecodeError:
                    pass
        
        # Strategy 5: All strategies failed
        return None
    
    def _clean_invalid_tokens(self, text: str) -> str:
        """
        Clean invalid JSON tokens from text.
        
        Removes:
        - Trailing commas before } or ]
        - Single quotes (replace with double quotes)
        - Newlines within strings
        - Control characters
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        # Remove trailing commas
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        
        # Replace single quotes with double quotes (risky but sometimes works)
        # Only do this outside of already-quoted strings
        text = text.replace("'", '"')
        
        # Remove control characters except newline/tab
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        
        # Remove newlines within JSON (keep structure)
        # This is aggressive - only use if needed
        # text = text.replace('\n', ' ')
        
        return text
    
    def _validate_output(self, result: Dict) -> bool:
        """Validate that output has required keys."""
        required_keys = ["predictions", "explanation"]
        return all(key in result for key in required_keys)
    
    def _deterministic_fallback(
        self,
        patient_summary: str,
        candidates: List[Tuple[str, float]],
        dag: Dict,
        summaries: List[Dict],
        clinician_comment: str
    ) -> Dict:
        """
        Deterministic fallback ranking when model fails.
        
        Formula: final_score = 0.6*transition_score + 0.3*doc_similarity_max + 0.1*clinician_boost
        """
        # Build similarity map from summaries
        similarity_map = {}
        for summary in summaries:
            disease_code = summary["disease_code"]
            similarity = summary["similarity"]
            if disease_code not in similarity_map:
                similarity_map[disease_code] = similarity
            else:
                similarity_map[disease_code] = max(similarity_map[disease_code], similarity)
        
        # Compute final scores
        scored_candidates = []
        for disease_code, transition_score in candidates:
            doc_similarity = similarity_map.get(disease_code, 0.0)
            
            # Clinician boost: check if comment mentions this disease
            clinician_boost = 0.0
            if clinician_comment:
                comment_lower = clinician_comment.lower()
                code_lower = disease_code.lower()
                if code_lower in comment_lower or any(
                    keyword in comment_lower
                    for keyword in ["kidney", "heart", "diabetes", "hypertension"]
                ):
                    clinician_boost = 0.2
            
            # Calculate DAG support score
            dag_score = 0.0
            for edge in dag.get("edges", []):
                if edge.get("to") == disease_code or edge.get("from") == disease_code:
                    dag_score = max(dag_score, edge.get("weight", 0.5))
            
            final_score = (
                0.6 * transition_score +
                0.3 * doc_similarity +
                0.1 * clinician_boost
            )
            
            scored_candidates.append({
                "code": disease_code,
                "score": round(final_score, 3),
                "transition_score": round(transition_score, 3),
                "doc_similarity": round(doc_similarity, 3),
                "dag_score": round(dag_score, 3),
                "clinician_boost": round(clinician_boost, 3)
            })
        
        # Sort by final score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # Assign ranks
        for rank, candidate in enumerate(scored_candidates, 1):
            candidate["rank"] = rank
        
        # Generate explanation (templated)
        top_candidate = scored_candidates[0] if scored_candidates else None
        if top_candidate:
            explanation = (
                f"Based on transition probability ({top_candidate['transition_score']:.2f}) "
                f"and document evidence ({top_candidate['doc_similarity']:.2f}), "
                f"{top_candidate['code']} is the most likely progression. "
            )
            if clinician_comment:
                explanation += f"Clinician input considered: {clinician_comment[:100]}"
        else:
            explanation = "No clear progression identified."
        
        # Trim explanation to 800 chars
        explanation = explanation[:800]
        
        # Build evidence list
        evidence = []
        for summary in summaries[:5]:
            evidence.append({
                "doc_id": summary["doc_id"],
                "disease_code": summary.get("disease_code", "Medical Knowledge"),
                "snippet": summary.get("summary", summary.get("snippet", ""))[:150],
                "similarity": round(summary["similarity"], 3)
            })
        
        return {
            "predictions": scored_candidates[:10],  # Top 10
            "explanation": explanation,
            "evidence": evidence,
            "dag": dag,
            "fallback": True
        }
    
    def generate_streaming(self, prompt: str) -> Generator[str, None, None]:
        """
        Generate streaming output (optional for future use).
        
        Args:
            prompt: Input prompt
            
        Yields:
            Generated text chunks
        """
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to(self.device)
        
        # Note: Streaming generation is complex with transformers
        # This is a simplified version
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=300,
                num_beams=1,
                do_sample=True,
                temperature=0.7
            )
        
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Yield in chunks
        chunk_size = 50
        for i in range(0, len(generated_text), chunk_size):
            yield generated_text[i:i+chunk_size]
