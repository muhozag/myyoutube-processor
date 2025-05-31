"""
AI utilities module for interacting with various AI services.
This module provides a unified interface for different AI backends.
"""

import logging
import os
import time
from typing import Optional

# Import specific AI service modules
try:
    from .mistral.mistral_utils import get_mistral_summary as get_mistral_api_summary
    from .mistral.mistral_utils import get_mistral_summary_with_requests
except ImportError:
    logging.warning("Mistral API utilities not available.")
    get_mistral_api_summary = None
    get_mistral_summary_with_requests = None

try:
    from .ollama_utils import get_mistral_summary as get_ollama_summary, is_ollama_available
except ImportError:
    logging.warning("Ollama utilities not available.")
    get_ollama_summary = None
    
    # Define a placeholder for ollama availability check if import failed
    def is_ollama_available():
        return False

logger = logging.getLogger(__name__)

def get_mistral_summary(text: str, max_length: int = 32000) -> Optional[str]:
    """
    Main entry point for AI-powered text summarization.
    Automatically selects the best available AI backend based on configuration.
    
    This function provides a unified interface that tries multiple AI backends
    in order of preference:
    1. Mistral API (if MISTRAL_API_KEY is set)
    2. Local Ollama (if available)
    
    Args:
        text (str): The text to summarize
        max_length (int): Maximum text length to process
        
    Returns:
        Optional[str]: Generated summary or None if all backends fail
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for summarization")
        return None
    
    # Try Mistral API first if configured
    mistral_api_key = os.environ.get('MISTRAL_API_KEY')
    if mistral_api_key and get_mistral_api_summary:
        logger.info("Attempting summary generation using Mistral API")
        try:
            summary = get_mistral_api_summary(text, max_length)
            if summary:
                logger.info("Successfully generated summary using Mistral API")
                return summary
            else:
                logger.warning("Mistral API returned empty summary, falling back to Ollama")
        except Exception as e:
            logger.warning(f"Mistral API failed: {str(e)}, falling back to Ollama")
    
    # Try Ollama if available
    if get_ollama_summary and is_ollama_available():
        logger.info("Attempting summary generation using Ollama")
        try:
            summary = get_ollama_summary(text, max_length)
            if summary:
                logger.info("Successfully generated summary using Ollama")
                return summary
            else:
                logger.warning("Ollama returned empty summary")
        except Exception as e:
            logger.error(f"Ollama failed: {str(e)}")
    
    logger.error("All AI backends failed or are unavailable")
    return None

def get_available_backends() -> list[str]:
    """
    Get a list of currently available AI backends.
    
    Returns:
        list[str]: List of available backend names
    """
    backends = []
    
    # Check Mistral API
    if os.environ.get('MISTRAL_API_KEY') and get_mistral_api_summary:
        backends.append("Mistral API")
    
    # Check Ollama
    if get_ollama_summary and is_ollama_available():
        backends.append("Ollama")
    
    return backends

def get_current_backend() -> str:
    """
    Get the name of the currently preferred AI backend.
    
    Returns:
        str: Name of the current backend or "None" if none available
    """
    available = get_available_backends()
    if available:
        return available[0]  # First one is preferred
    return "None"