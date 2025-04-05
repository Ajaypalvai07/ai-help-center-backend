from main import app
import logging
from fastapi import FastAPI
from core.logging_config import configure_logging

# Configure logging for serverless environment
configure_logging()
logger = logging.getLogger(__name__)

# Log startup information
logger.info("Initializing serverless function")

# Vercel serverless function handler
handler = app

# Log successful initialization
logger.info("Serverless function initialized successfully") 