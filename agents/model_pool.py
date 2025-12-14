"""
Model Pool - Singleton manager for all AI models

Ensures models are loaded once at startup and reused across requests.
Provides warmup inference for faster first response.
"""

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sentence_transformers import SentenceTransformer
from typing import Tuple, Optional
import time


class ModelPool:
    """
    Singleton pool for managing AI models.
    
    Ensures models are loaded once and reused across all requests.
    """
    
    _instance: Optional['ModelPool'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize model pool (only runs once)."""
        if ModelPool._initialized:
            return
        
        print("=" * 60)
        print("Initializing Model Pool...")
        print("=" * 60)
        
        # Model references
        self.embedding_model: Optional[SentenceTransformer] = None
        self.slm_tokenizer: Optional[AutoTokenizer] = None
        self.slm_model: Optional[AutoModelForSeq2SeqLM] = None
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load status
        self.embedding_loaded = False
        self.slm_loaded = False
        
        ModelPool._initialized = True
    
    def load_embedding_model(self, model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
        """
        Load or get embedding model.
        
        Args:
            model_name: Sentence-transformer model name
            
        Returns:
            SentenceTransformer model
        """
        if not self.embedding_loaded:
            start_time = time.time()
            print(f"📦 Loading embedding model: {model_name}...")
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_loaded = True
            elapsed = time.time() - start_time
            print(f"✅ Embedding model loaded in {elapsed:.2f}s")
        
        return self.embedding_model
    
    def load_slm_model(
        self,
        model_name: str = "google/flan-t5-base"
    ) -> Tuple[AutoTokenizer, AutoModelForSeq2SeqLM, str]:
        """
        Load or get SLM model and tokenizer.
        
        Args:
            model_name: HuggingFace model name
            
        Returns:
            Tuple of (tokenizer, model, device)
        """
        if not self.slm_loaded:
            start_time = time.time()
            print(f"📦 Loading SLM model: {model_name} on {self.device}...")
            self.slm_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.slm_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self.slm_model.to(self.device)
            self.slm_model.eval()
            self.slm_loaded = True
            elapsed = time.time() - start_time
            print(f"✅ SLM model loaded in {elapsed:.2f}s")
        
        return self.slm_tokenizer, self.slm_model, self.device
    
    def warmup_models(self):
        """
        Perform warmup inference on all models for faster first response.
        
        This runs a dummy inference to initialize CUDA kernels and caches.
        """
        print("\n🔥 Warming up models...")
        
        # Warmup embedding model
        if self.embedding_loaded and self.embedding_model:
            start_time = time.time()
            _ = self.embedding_model.encode(["warmup text"], show_progress_bar=False)
            elapsed = time.time() - start_time
            print(f"   ✓ Embedding model warmed up in {elapsed:.3f}s")
        
        # Warmup SLM model
        if self.slm_loaded and self.slm_tokenizer and self.slm_model:
            start_time = time.time()
            inputs = self.slm_tokenizer(
                "warmup prompt",
                return_tensors="pt",
                max_length=50,
                truncation=True
            ).to(self.device)
            
            with torch.no_grad():
                _ = self.slm_model.generate(
                    **inputs,
                    max_length=20,
                    num_beams=1
                )
            elapsed = time.time() - start_time
            print(f"   ✓ SLM model warmed up in {elapsed:.3f}s")
        
        print("✅ All models ready!\n")
    
    def get_model_status(self) -> dict:
        """
        Get status of all models.
        
        Returns:
            Dict with model loading status
        """
        return {
            "embedding_loaded": self.embedding_loaded,
            "slm_loaded": self.slm_loaded,
            "device": self.device,
            "initialized": ModelPool._initialized
        }


# Global singleton instance
_model_pool = ModelPool()


def get_model_pool() -> ModelPool:
    """
    Get the global model pool instance.
    
    Returns:
        ModelPool singleton
    """
    return _model_pool
