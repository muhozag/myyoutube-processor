"""
AI utilities module for interacting with various AI services.
This module provides a unified interface for different AI backends.
"""

import logging
import os
import time
import socket
from typing import Optional

# Import specific AI service modules
try:
    from .mistral.mistral_utils import get_mistral_summary as get_mistral_api_summary
except ImportError:
    logging.warning("Mistral API utilities not available.")
    get_mistral_api_summary = None

try:
    from .ollama_utils import get_mistral_summary as get_ollama_summary, is_ollama_available
except ImportError:
    logging.warning("Ollama utilities not available.")
    get_ollama_summary = None
    
    # Define a placeholder for ollama availability check if import failed
    def is_ollama_available():
        return False

logger = logging.getLogger(__name__)

def is_railway_environment() -> bool:
    """
    Detect if the application is running on Railway.app.
    
    Returns:
        bool: True if running on Railway, False otherwise
    """
    return os.getenv('RAILWAY_ENVIRONMENT') is not None or os.getenv('RAILWAY') is not None

def get_ai_summary(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate a summary using one of the available AI services.
    This function tries different AI services based on the deployment environment.
    
    Args:
        text (str): The text to summarize
        max_length (int): Maximum text length to send to the AI service
        
    Returns:
        Optional[str]: The generated summary or None if all services failed
    """
    start_time = time.time()
    logger.info("Starting AI summary generation")
    
    # Check if text is valid
    if not text or not text.strip():
        logger.error("Cannot generate summary: Empty text provided")
        return None
        
    # Determine the environment
    running_on_railway = is_railway_environment()
    logger.info(f"Detected environment: {'Railway' if running_on_railway else 'Local'}")
    
    # For Railway deployment, use Mistral API
    if running_on_railway:
        # Try Mistral API first (if available and API key exists)
        if get_mistral_api_summary and os.getenv('MISTRAL_API_KEY'):
            try:
                logger.info("Using Mistral API for Railway deployment")
                mistral_summary = get_mistral_api_summary(text, max_length)
                if mistral_summary:
                    elapsed = time.time() - start_time
                    logger.info(f"Summary generated with Mistral API in {elapsed:.2f} seconds")
                    return mistral_summary
                logger.warning("Mistral API summary generation failed")
            except Exception as e:
                logger.exception(f"Error using Mistral API for summary: {str(e)}")
        else:
            logger.error("Mistral API unavailable or API key not found - required for Railway deployment")
    # For local development, use Ollama
    else:
        # Check if Ollama is available (should check service connection)
        ollama_available = is_ollama_available()
        logger.info(f"Ollama service available: {ollama_available}")
        
        if ollama_available and get_ollama_summary:
            try:
                logger.info("Using Ollama for local development environment")
                ollama_summary = get_ollama_summary(text, max_length)
                if ollama_summary:
                    elapsed = time.time() - start_time
                    logger.info(f"Summary generated with Ollama in {elapsed:.2f} seconds")
                    return ollama_summary
                logger.warning("Ollama summary generation failed")
            except Exception as e:
                logger.exception(f"Error using Ollama for summary: {str(e)}")
        else:
            logger.warning("Ollama service not available for local development")
            
        # Only try Mistral API as fallback for local if Ollama fails and API key exists
        if get_mistral_api_summary and os.getenv('MISTRAL_API_KEY'):
            try:
                logger.info("Ollama failed or unavailable, trying Mistral API as fallback in local environment")
                mistral_summary = get_mistral_api_summary(text, max_length)
                if mistral_summary:
                    elapsed = time.time() - start_time
                    logger.info(f"Summary generated with Mistral API fallback in {elapsed:.2f} seconds")
                    return mistral_summary
            except Exception as e:
                logger.exception(f"Error using Mistral API fallback: {str(e)}")
    
    elapsed = time.time() - start_time
    logger.error(f"All summary generation methods failed after {elapsed:.2f} seconds")
    return None