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

def is_railway_environment() -> bool:
    """
    Detect if code is running in Railway environment.
    
    Returns:
        True if running on Railway, False otherwise
    """
    return bool(os.getenv('RAILWAY_ENVIRONMENT') or 
                os.getenv('RAILWAY_PROJECT_ID') or 
                os.getenv('RAILWAY_SERVICE_ID'))

def get_ai_summary(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate an AI summary of the given text using available services.
    Tries multiple approaches based on the deployment environment:
    1. Ollama (if available)
    2. Mistral API (as fallback or primary on Railway)
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model
        
    Returns:
        The generated summary, or None if all attempts failed
    """
    start_time = time.time()
    
    # Check environment
    railway_env = is_railway_environment()
    
    # Log the environment
    logger.info(f"Running in Railway environment: {railway_env}")
    
    # For Railway, prioritize Mistral API over Ollama
    if railway_env:
        logger.info("Railway environment detected, prioritizing Mistral API for reliability")
        if get_mistral_api_summary:
            try:
                logger.info("Using Mistral API for summary generation")
                mistral_summary = get_mistral_api_summary(text, max_length)
                if mistral_summary:
                    elapsed = time.time() - start_time
                    logger.info(f"Summary generated with Mistral API in {elapsed:.2f} seconds")
                    return mistral_summary
                logger.warning("Mistral API summary generation failed")
            except Exception as e:
                logger.exception(f"Error using Mistral API for summary: {str(e)}")
                
            # If standard Mistral API call fails, try the requests-based approach
            if get_mistral_summary_with_requests:
                try:
                    logger.info("Falling back to requests-based Mistral API implementation")
                    requests_summary = get_mistral_summary_with_requests(text, max_length)
                    if requests_summary:
                        elapsed = time.time() - start_time
                        logger.info(f"Summary generated with requests-based Mistral API in {elapsed:.2f} seconds")
                        return requests_summary
                    logger.warning("Requests-based Mistral API summary generation failed")
                except Exception as e:
                    logger.exception(f"Error using requests-based Mistral API for summary: {str(e)}")
        else:
            logger.error("Mistral API utilities not available - required for Railway deployment")
    
    # For all environments, try Ollama if it's available
    ollama_available = is_ollama_available()
    logger.info(f"Remote Ollama service available: {ollama_available}")
    
    if ollama_available and get_ollama_summary:
        try:
            logger.info("Using remote Ollama service")
            ollama_summary = get_ollama_summary(text, max_length)
            if ollama_summary:
                elapsed = time.time() - start_time
                logger.info(f"Summary generated with Ollama in {elapsed:.2f} seconds")
                return ollama_summary
            logger.warning("Ollama summary generation failed")
        except Exception as e:
            logger.exception(f"Error using Ollama for summary: {str(e)}")
    else:
        logger.warning("Ollama service not available")
    
    # For non-Railway environments, try Mistral API as fallback
    if not railway_env and get_mistral_api_summary and os.getenv('MISTRAL_API_KEY'):
        try:
            logger.info("Using Mistral API as fallback")
            mistral_summary = get_mistral_api_summary(text, max_length)
            if mistral_summary:
                elapsed = time.time() - start_time
                logger.info(f"Summary generated with Mistral API in {elapsed:.2f} seconds")
                return mistral_summary
            logger.warning("Mistral API summary generation failed")
        except Exception as e:
            logger.exception(f"Error using Mistral API for summary: {str(e)}")
    
    # If all methods failed, return a placeholder or null
    logger.error("All summary generation methods failed")
    return None