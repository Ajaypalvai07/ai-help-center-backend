from typing import List, Dict, Any
import numpy as np
from datetime import datetime
import logging
from core.config import settings

logger = logging.getLogger(__name__)

class MLEngine:
    def __init__(self):
        """Initialize the ML Engine with basic text processing capabilities"""
        logger.info("Initializing ML Engine with basic text processing")
        self.cache = {}
        
    def _get_simple_embedding(self, text: str) -> List[float]:
        """Generate a simple embedding based on word frequencies"""
        # Simple word frequency-based embedding
        words = text.lower().split()
        embedding = np.zeros(100)  # Using 100-dimensional space
        
        for i, word in enumerate(words):
            # Use hash of word to determine the position
            pos = hash(word) % 100
            embedding[pos] += 1
            
        # Normalize the embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding.tolist()

    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    async def find_similar_queries(self, query: str, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Find similar queries from the cache"""
        try:
            query_embedding = self._get_simple_embedding(query)
            similar_queries = []
            
            for cached_query, data in self.cache.items():
                similarity = self._calculate_similarity(query_embedding, data["embedding"])
                if similarity > threshold:
                    similar_queries.append({
                        "query": cached_query,
                        "similarity": similarity,
                        "category": data.get("category", "General"),
                        "timestamp": data.get("timestamp", datetime.utcnow().isoformat())
                    })
            
            # Sort by similarity score
            similar_queries.sort(key=lambda x: x["similarity"], reverse=True)
            return similar_queries[:5]  # Return top 5 similar queries
            
        except Exception as e:
            logger.error(f"Error finding similar queries: {str(e)}")
            return []

    async def add_to_cache(self, query: str, category: str):
        """Add a query to the cache with its embedding"""
        try:
            embedding = self._get_simple_embedding(query)
            self.cache[query] = {
                "embedding": embedding,
                "category": category,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Keep cache size manageable
            if len(self.cache) > 1000:
                # Remove oldest entries
                sorted_queries = sorted(self.cache.items(), key=lambda x: x[1]["timestamp"])
                self.cache = dict(sorted_queries[-1000:])
                
        except Exception as e:
            logger.error(f"Error adding query to cache: {str(e)}")

# Initialize singleton instance
ml_engine = MLEngine()