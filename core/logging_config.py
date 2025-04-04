import logging

def configure_logging():
    """Configure logging settings for the application"""
    # Set log levels for different loggers
    loggers_to_silence = [
        "uvicorn.access",
        "pymongo",
        "motor",
        "multipart",
        "passlib",
        "core.auth"
    ]
    
    for logger_name in loggers_to_silence:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Configure uvicorn logger to show only INFO and above
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'  # Simple format showing only the message
    ) 