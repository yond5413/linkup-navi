import cohere
import faiss
import numpy as np
import pickle
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import get_settings

settings = get_settings()

class VectorMemoryService:
    def __init__(self, index_name: str = "long_term_memory"):
        self.index_name = index_name
        self.memory_path = settings.memory_path
        self.index_file = self.memory_path / f"{index_name}.index"
        self.metadata_file = self.memory_path / f"{index_name}.pkl"
        
        self.co = cohere.Client(settings.cohere_api_key) if settings.cohere_api_key else None
        self.dimension = 1024  # Default for embed-english-v3.0
        
        self.index = None
        self.metadata = []
        
        self._load_memory()

    def _load_memory(self):
        """Loads the FAISS index and metadata from disk if they exist."""
        if self.index_file.exists() and self.metadata_file.exists():
            print(f"Loading existing memory from {self.index_file}")
            self.index = faiss.read_index(str(self.index_file))
            with open(self.metadata_file, "rb") as f:
                self.metadata = pickle.load(f)
        else:
            print("Initializing new memory index")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []

    def _save_memory(self):
        """Saves the FAISS index and metadata to disk."""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, "wb") as f:
            pickle.dump(self.metadata, f)

    def add_to_memory(self, text: str):
        """Embeds text and adds it to the FAISS index."""
        if not self.co:
            print("Cohere API key not configured. Cannot add to memory.")
            return

        # Get embeddings from Cohere
        response = self.co.embed(
            texts=[text],
            model="embed-english-v3.0",
            input_type="search_document",
            embedding_types=["float"]
        )
        
        # In Cohere 5.x, response.embeddings.float_ is a list of lists
        embedding = np.array(response.embeddings.float_).astype("float32")
        
        # Add to FAISS index
        self.index.add(embedding)
        
        # Save metadata (the actual text)
        self.metadata.append(text)
        
        # Persist to disk
        self._save_memory()
        print(f"Added to memory: {text[:50]}...")

    def query_memory(self, query: str, top_k: int = 5) -> List[str]:
        """Queries the memory for the most relevant text chunks."""
        if not self.co or self.index.ntotal == 0:
            return []

        # Get query embedding
        response = self.co.embed(
            texts=[query],
            model="embed-english-v3.0",
            input_type="search_query",
            embedding_types=["float"]
        )
        
        query_embedding = np.array(response.embeddings.float_).astype("float32")
        
        # Search index
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Retrieve relevant metadata
        results = []
        for idx in indices[0]:
            if idx != -1 and idx < len(self.metadata):
                results.append(self.metadata[idx])
        
        return results

# Singleton instance
_vector_memory_service = None

def get_vector_memory_service() -> VectorMemoryService:
    global _vector_memory_service
    if _vector_memory_service is None:
        _vector_memory_service = VectorMemoryService()
    return _vector_memory_service
