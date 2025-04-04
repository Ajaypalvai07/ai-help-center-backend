from typing import Dict, Any, List
from datetime import datetime
from .config import settings
import logging
import json
import httpx
from typing import Union

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        """Initialize the AI Engine with Hugging Face API configuration"""
        try:
            self.api_url = "https://api-inference.huggingface.co/models/"
            self.headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
            self.model_name = settings.AI_MODEL_NAME
            self.client = None
            self.is_initialized = bool(settings.HUGGINGFACE_API_KEY)
            if not self.is_initialized:
                logger.warning("HUGGINGFACE_API_KEY not set. AI Engine will not be operational.")
            else:
                logger.info("AIEngine initialized successfully with Hugging Face API")
        except Exception as e:
            logger.error(f"Error initializing AIEngine: {str(e)}")
            self.is_initialized = False
            raise

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                headers=self.headers,
                timeout=settings.REQUEST_TIMEOUT
            )
        return self.client

    async def process_query(
        self,
        query: str,
        context: Dict[str, Any],
        user_skill_level: str = "beginner",
        language: str = "en"
    ) -> Dict[str, Any]:
        """Process user query with context-aware AI response"""
        if not self.is_initialized:
            return {
                "error": "AI Engine not initialized",
                "details": "HUGGINGFACE_API_KEY not set",
                "needs_human": True,
                "confidence_score": 0.0
            }

        try:
            # Generate solution
            solution = await self.generate_solution(
                query=query,
                context=context,
                user_skill_level=user_skill_level,
                language=language
            )
            
            # Calculate confidence
            confidence_score = self.calculate_confidence(solution)
            
            return {
                "solution": solution,
                "needs_human": self.check_needs_human(solution),
                "confidence_score": confidence_score,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "error": "Failed to process query",
                "details": str(e),
                "needs_human": True,
                "confidence_score": 0.0
            }

    async def generate_solution(
        self,
        query: str,
        context: Dict[str, Any],
        user_skill_level: str,
        language: str
    ) -> Dict[str, Any]:
        """Generate comprehensive solution using Hugging Face API"""
        try:
            # Prepare prompt
            prompt = f"""
            Given the technical issue: {query}
            User skill level: {user_skill_level}
            Context: {json.dumps(context)}
            
            Provide a detailed solution with:
            1. Root cause analysis
            2. Step-by-step resolution steps
            3. Code examples if relevant
            4. Verification steps
            5. Preventive measures
            """
            
            # Make API request to Hugging Face
            client = await self.get_client()
            response = await client.post(
                f"{self.api_url}{self.model_name}",
                json={"inputs": prompt}
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed: {response.text}")
            
            result = response.json()
            generated_text = result[0]["generated_text"]
            
            return {
                "response": generated_text,
                "steps": self.extract_steps(generated_text),
                "code_samples": self.extract_code_samples(generated_text),
                "verification": self.extract_verification_steps(generated_text)
            }
            
        except Exception as e:
            logger.error(f"Error generating solution: {str(e)}")
            raise

    def check_needs_human(self, solution: Dict[str, Any]) -> bool:
        """Determine if human intervention is needed"""
        try:
            return (
                solution.get("confidence_score", 1.0) < 0.7 or
                any(
                    flag in str(solution.get("response", "")).lower()
                    for flag in ["security", "compliance", "legal", "hardware"]
                )
            )
        except Exception as e:
            logger.error(f"Error checking human need: {str(e)}")
            return True

    def calculate_confidence(self, solution: Dict[str, Any]) -> float:
        """Calculate confidence score for the solution"""
        try:
            factors = {
                "has_steps": bool(solution.get("steps")),
                "has_code": bool(solution.get("code_samples")),
                "has_verification": bool(solution.get("verification")),
                "response_length": len(str(solution.get("response", ""))) > 100
            }
            
            weights = {
                "has_steps": 0.4,
                "has_code": 0.2,
                "has_verification": 0.2,
                "response_length": 0.2
            }
            
            score = sum(
                weights[factor] * float(value)
                for factor, value in factors.items()
            )
            
            return min(max(score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.0

    def extract_steps(self, response: str) -> List[str]:
        """Extract step-by-step instructions from response"""
        try:
            steps = []
            for line in response.split("\n"):
                if any(line.strip().startswith(str(i) + ".") for i in range(1, 10)):
                    steps.append(line.strip())
            return steps
        except Exception as e:
            logger.error(f"Error extracting steps: {str(e)}")
            return []

    def extract_code_samples(self, response: str) -> List[str]:
        """Extract code samples from response"""
        try:
            code_samples = []
            in_code_block = False
            current_block = []
            
            for line in response.split("\n"):
                if line.strip().startswith("```"):
                    if in_code_block:
                        code_samples.append("\n".join(current_block))
                        current_block = []
                    in_code_block = not in_code_block
                elif in_code_block:
                    current_block.append(line)
                    
            return code_samples
        except Exception as e:
            logger.error(f"Error extracting code samples: {str(e)}")
            return []

    def extract_verification_steps(self, response: str) -> List[str]:
        """Extract verification steps from response"""
        try:
            verification_steps = []
            in_verification = False
            
            for line in response.split("\n"):
                if "verif" in line.lower() or "test" in line.lower():
                    in_verification = True
                if in_verification and line.strip():
                    verification_steps.append(line.strip())
                if in_verification and not line.strip():
                    in_verification = False
                    
            return verification_steps
        except Exception as e:
            logger.error(f"Error extracting verification steps: {str(e)}")
            return []

    async def close(self):
        """Close the httpx client"""
        if self.client:
            await self.client.aclose()

# Initialize singleton instance
ai_engine = AIEngine()