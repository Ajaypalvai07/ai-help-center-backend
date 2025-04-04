from typing import List, Dict, Any
import numpy as np
from sklearn.cluster import KMeans
import pinecone
from ..core.config import settings
import redis
from datetime import datetime
import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk
from nltk.sentiment import SentimentIntensityAnalyzer

class NLPEngine:
    def __init__(self):
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('averaged_perceptron_tagger')
        try:
            nltk.data.find('chunkers/maxent_ne_chunker')
        except LookupError:
            nltk.download('maxent_ne_chunker')
        try:
            nltk.data.find('corpora/words')
        except LookupError:
            nltk.download('words')
        try:
            nltk.data.find('sentiment/vader_lexicon')
        except LookupError:
            nltk.download('vader_lexicon')

        # Initialize NLP components
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize Pinecone for vector similarity search
        pinecone.init(
            api_key=settings.PINECONE_API_KEY,
            environment=settings.PINECONE_ENV
        )
        self.index = pinecone.Index(settings.PINECONE_INDEX_NAME)
        
        # Initialize Redis for caching
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
        
        # Initialize query clustering
        self.kmeans = KMeans(n_clusters=10, random_state=42)
        self.query_embeddings = []
        self.query_texts = []

    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        # Extract entities using NLTK NER
        tokens = word_tokenize(query)
        pos_tags = pos_tag(tokens)
        named_entities = ne_chunk(pos_tags)
        entities = []
        for chunk in named_entities:
            if hasattr(chunk, 'label'):
                entities.append(((' '.join(c[0] for c in chunk)), chunk.label()))
        
        # Get query embedding
        query_embedding = await self.get_embedding(query)
        
        # Search for similar queries in Pinecone
        similar_queries = await self.search_similar_queries(query_embedding)
        
        # Get cached response if available
        cached_response = self.redis_client.get(f"query:{query}")
        if cached_response:
            return {
                "response": cached_response,
                "source": "cache",
                "entities": entities,
                "similar_queries": similar_queries
            }
        
        # Cluster the query
        cluster = await self.cluster_query(query_embedding)
        
        # Analyze sentiment
        sentiment_scores = self.sentiment_analyzer.polarity_scores(query)
        sentiment = {
            "compound": sentiment_scores["compound"],
            "positive": sentiment_scores["pos"],
            "negative": sentiment_scores["neg"],
            "neutral": sentiment_scores["neu"]
        }
        
        # Classify query intent based on keywords
        intent = self.classify_intent(query)
        
        # Analyze complexity
        complexity = self.analyze_complexity(query)
        
        # Extract technical requirements
        tech_requirements = self.extract_technical_requirements(query)
        
        return {
            "processed_query": query,
            "entities": entities,
            "embedding": query_embedding.tolist(),
            "cluster": cluster,
            "sentiment": sentiment,
            "intent": intent,
            "similar_queries": similar_queries,
            "complexity": complexity,
            "technical_requirements": tech_requirements,
            "context": context
        }

    def classify_intent(self, query: str) -> Dict[str, float]:
        """Classify query intent using keyword matching"""
        query_lower = query.lower()
        words = set(word_tokenize(query_lower))
        
        # Define intent keywords
        intent_keywords = {
            "technical_issue": {"error", "bug", "issue", "problem", "crash", "fix", "broken"},
            "feature_request": {"add", "feature", "implement", "support", "request", "enhance"},
            "bug_report": {"bug", "report", "error", "fail", "crash", "incorrect"},
            "general_inquiry": {"how", "what", "when", "where", "why", "help", "explain"}
        }
        
        # Calculate scores based on keyword matches
        scores = {}
        for intent, keywords in intent_keywords.items():
            matches = words.intersection(keywords)
            scores[intent] = len(matches) / len(keywords) if matches else 0.0
            
        # Normalize scores
        total = sum(scores.values()) or 1.0
        return {k: v/total for k, v in scores.items()}

    async def get_embedding(self, text: str) -> np.ndarray:
        # Simple bag-of-words embedding
        words = word_tokenize(text.lower())
        embedding = np.zeros(768)  # Keep same dimension for compatibility
        for i, word in enumerate(words):
            # Use hash of word to determine position
            pos = hash(word) % 768
            embedding[pos] = 1.0
        return embedding / (len(words) or 1)

    async def search_similar_queries(self, embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        # Search Pinecone index
        results = self.index.query(
            vector=embedding.tolist(),
            top_k=top_k,
            include_metadata=True
        )
        
        return [{
            "query": match.metadata["query"],
            "similarity": match.score,
            "timestamp": match.metadata.get("timestamp")
        } for match in results.matches]

    async def cluster_query(self, embedding: np.ndarray) -> int:
        # Add to existing embeddings
        self.query_embeddings.append(embedding)
        
        # Retrain clustering model periodically
        if len(self.query_embeddings) % 100 == 0:
            embeddings_array = np.array(self.query_embeddings)
            self.kmeans.fit(embeddings_array)
        
        # Get cluster for current query
        cluster = self.kmeans.predict([embedding])[0]
        return int(cluster)

    def analyze_complexity(self, query: str) -> float:
        """Analyze query complexity"""
        words = word_tokenize(query)
        pos_tags = pos_tag(words)
        
        # Factors affecting complexity
        sentence_length = len(words)
        technical_terms = len([word for word, tag in pos_tags if tag.startswith('NN')])
        verb_complexity = len([word for word, tag in pos_tags if tag.startswith('VB')])
        
        # Calculate complexity score (0-1)
        complexity = (
            0.4 * (technical_terms / max(sentence_length, 1)) +
            0.3 * (sentence_length / 50) +  # Normalize by max expected length
            0.3 * (verb_complexity / max(sentence_length, 1))
        )
        
        return min(max(complexity, 0), 1)  # Ensure score is between 0 and 1

    def extract_technical_requirements(self, query: str) -> List[str]:
        """Extract technical requirements from query"""
        words = word_tokenize(query.lower())
        pos_tags = pos_tag(words)
        requirements = []
        
        # Technical requirement patterns
        tech_terms = {
            "access", "permission", "credential", "token", "key",
            "database", "server", "api", "endpoint", "configuration"
        }
        
        for i, (word, tag) in enumerate(pos_tags):
            if word in tech_terms:
                if i > 0:
                    prev_word, prev_tag = pos_tags[i-1]
                    if prev_tag.startswith('JJ') or prev_tag.startswith('NN'):
                        requirements.append(f"{prev_word} {word}")
                if i < len(pos_tags) - 1:
                    next_word, next_tag = pos_tags[i+1]
                    if next_tag.startswith('NN'):
                        requirements.append(f"{word} {next_word}")
        
        return requirements

    async def cache_response(self, query: str, response: str, ttl: int = 3600):
        # Cache the response in Redis
        self.redis_client.setex(
            f"query:{query}",
            ttl,
            response
        )

    async def update_knowledge_base(self, query: str, response: str, feedback: Dict[str, Any]):
        # Get query embedding
        embedding = await self.get_embedding(query)
        
        # Store in Pinecone with metadata
        self.index.upsert([
            (
                f"query_{datetime.now().timestamp()}",
                embedding.tolist(),
                {
                    "query": query,
                    "response": response,
                    "feedback": feedback,
                    "timestamp": datetime.now().isoformat()
                }
            )
        ])

nlp_engine = NLPEngine()