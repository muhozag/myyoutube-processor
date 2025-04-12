"""
AI service module that abstracts the underlying AI implementation.
This module dynamically selects between local Ollama and cloud Mistral API
based on the environment.
"""
import os
import logging
from typing import Optional

# Import both implementations
from myyoutubeprocessor.utils.ai.ollama_utils import get_mistral_summary as get_ollama_summary
from myyoutubeprocessor.utils.ai.mistral.mistral_utils import get_mistral_summary as get_mistral_api_summary

logger = logging.getLogger(__name__)

def is_railway_environment():
    """
    Check if the current environment is Railway.
    
    Returns:
        bool: True if running on Railway, False otherwise
    """
    return bool(os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('RAILWAY_SERVICE_NAME'))

def get_ai_summary(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate a summary of the given text using the appropriate AI service.
    Uses Mistral API in production and Ollama in development.
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model
        
    Returns:
        A summary of the text, or None if an error occurred
    """
    # Determine which implementation to use
    if is_railway_environment():
        logger.info("Using Mistral API for summary generation (Railway environment)")
        return get_mistral_api_summary(text, max_length)
    else:
        logger.info("Using local Ollama for summary generation (development environment)")
        return get_ollama_summary(text, max_length)