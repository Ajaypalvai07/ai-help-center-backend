from typing import Dict, Any, Optional, List
import httpx
from core.config import settings
from core.ml_engine import ml_engine
from services.mongodb import mongodb_service
import json
import logging
import sys
import os
from datetime import datetime
from fastapi import HTTPException
import asyncio

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        """Initialize the AI service with Ollama and/or Hugging Face"""
        try:
            self.model_name = "mistral"  # Default model for Ollama
            self.ollama_base_url = "http://localhost:11434"
            self.client = httpx.AsyncClient(base_url=self.ollama_base_url, timeout=60.0)
            
            # Initialize Hugging Face client if configured
            self.hf_client = None
            if settings.USE_HUGGINGFACE and settings.HUGGINGFACE_API_KEY:
                self.hf_client = httpx.AsyncClient(
                    base_url="https://api-inference.huggingface.co/models",
                    headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"},
                    timeout=30.0
                )
                logger.info("✅ Hugging Face API client initialized")
            
            logger.info("✅ AI Service initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing AI service: {str(e)}")
            self.client = None

    async def generate_solution(self, query: str, category: str, context: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a solution using available AI services"""
        try:
            # Try Hugging Face first if configured
            if self.hf_client and settings.USE_HUGGINGFACE:
                try:
                    return await self._generate_huggingface(query, category, context)
                except Exception as e:
                    logger.error(f"❌ Hugging Face API error: {str(e)}")
                    # Fall through to Ollama if Hugging Face fails
            
            # Try Ollama if available
            if self.client:
                return await self._generate_ollama(query, category, context)
            
            # Use fallback if both services fail
            return await self._generate_fallback(query, category)

        except Exception as e:
            logger.error(f"❌ Unexpected error in generate_solution: {str(e)}")
            return await self._generate_fallback(query, category)

    async def _generate_huggingface(self, query: str, category: str, context: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a solution using Hugging Face API"""
        try:
            # Format prompt with context
            prompt = f"Category: {category}\n\n"
            if context:
                for msg in context[-3:]:
                    role = "User" if msg.get("is_user", True) else "Assistant"
                    prompt += f"{role}: {msg['content']}\n"
            prompt += f"\nUser: {query}\nAssistant:"

            # Make request to Hugging Face API
            response = await self.hf_client.post(
                f"/{settings.HUGGINGFACE_MODEL}",
                json={"inputs": prompt, "parameters": {"max_length": 512}}
            )
            response.raise_for_status()
            result = response.json()
            
            generated_text = result[0]["generated_text"].strip()
            
            if not generated_text:
                raise ValueError("Empty response from Hugging Face API")
                
            logger.info("✅ Successfully generated AI response using Hugging Face API")
            
            return {
                "content": generated_text,
                "confidence": 0.9,
                "created_at": datetime.utcnow().isoformat(),
                "category": category,
                "metrics": {
                    "length": len(generated_text),
                    "model": settings.HUGGINGFACE_MODEL,
                    "provider": "huggingface"
                }
            }

        except Exception as e:
            logger.error(f"❌ Hugging Face API error: {str(e)}")
            raise

    async def _generate_ollama(self, query: str, category: str, context: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a solution using local Ollama model"""
        try:
            if not self.client:
                return await self._generate_fallback(query, category)

            # Format the conversation for Ollama
            messages = []
            if context:
                for msg in context[-3:]:  # Only use last 3 messages for context
                    messages.append({
                        "role": "user" if msg.get("is_user", True) else "assistant",
                        "content": msg["content"]
                    })

            # Add system prompt for context
            system_prompt = f"You are a helpful AI assistant specialized in {category} topics. Provide clear and concise responses."
            
            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *messages,
                    {"role": "user", "content": query}
                ],
                "stream": False
            }

            try:
                # Make request to Ollama API
                response = await self.client.post("/api/chat", json=payload)
                response.raise_for_status()
                result = response.json()
                
                generated_text = result["message"]["content"].strip()
                
                if not generated_text:
                    raise ValueError("Empty response from AI service")
                    
                logger.info("✅ Successfully generated AI response using Ollama")
                
                return {
                    "content": generated_text,
                    "confidence": 0.85,
                    "created_at": datetime.utcnow().isoformat(),
                    "category": category,
                    "metrics": {
                        "length": len(generated_text),
                        "model": self.model_name,
                        "local": True
                    }
                }

            except httpx.HTTPStatusError as e:
                logger.error(f"❌ Ollama API error: {str(e)}")
                return await self._generate_fallback(query, category)

        except Exception as e:
            logger.error(f"❌ Unexpected error in generate_solution: {str(e)}")
            return await self._generate_fallback(query, category)

    async def _generate_fallback(self, query: str, category: str) -> Dict[str, Any]:
        """Generate a fallback response when AI service is unavailable"""
        try:
            base_response = (
                "⚠️ The local AI service (Ollama) is currently unavailable.\n\n"
                "To resolve this:\n"
                "1. Ensure Ollama is installed (https://ollama.com)\n"
                "2. Run 'ollama run mistral' in your terminal\n"
                "3. Check if Ollama is running on http://localhost:11434\n"
                "4. Restart the server\n\n"
                "Let me help you with alternative solutions:"
            )

            solutions = []
            confidence = 0.3

            # Try to find similar queries from the database
            similar = await ml_engine.find_similar_queries(query)
            if similar:
                best_match = similar[0]
                solutions.append(f"\n\n🔍 Found a similar question:\n{best_match['query']}")
                if 'solution' in best_match:
                    solutions.append(f"\n💡 Previous solution:\n{best_match['solution']}")
                confidence = best_match['similarity']

            # Add category-specific troubleshooting steps
            troubleshooting = self._get_category_troubleshooting(category)
            if troubleshooting:
                solutions.append(f"\n\n🔧 Common troubleshooting steps for {category}:")
                solutions.append(troubleshooting)

            # Combine all solutions
            final_response = base_response + "".join(solutions)

            return {
                "content": final_response,
                "confidence": confidence,
                "created_at": datetime.utcnow().isoformat(),
                "category": category,
                "metrics": {
                    "length": len(final_response),
                    "model": "fallback",
                    "is_fallback": True,
                    "has_similar_cases": bool(similar)
                }
            }
        except Exception as e:
            logger.error(f"Error in fallback response: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable. Please try again later."
            )

    def _get_category_troubleshooting(self, category: str) -> str:
        """Get category-specific troubleshooting steps"""
        troubleshooting_guides = {
            "Technical": (
                "1. Check if Ollama is running (ollama list)\n"
                "2. Verify model is downloaded (ollama pull mistral)\n"
                "3. Check system resources\n"
                "4. Restart Ollama service if needed\n"
                "5. Check network connectivity"
            ),
            "General": (
                "1. Clear application cache\n"
                "2. Check for Ollama updates\n"
                "3. Verify model availability\n"
                "4. Review recent changes\n"
                "5. Check system requirements"
            )
        }
        return troubleshooting_guides.get(category, "")

# Initialize singleton instance
ai_service = AIService()