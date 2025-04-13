"""
AI utilities module for interacting with Ollama models.
"""
import logging
import ollama
import re
import datetime
import time
import socket
import os
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Default Ollama settings
DEFAULT_OLLAMA_HOST = "localhost"
DEFAULT_OLLAMA_PORT = 11434

# Configure ollama client with custom host/port
def configure_ollama(host=DEFAULT_OLLAMA_HOST, port=DEFAULT_OLLAMA_PORT):
    """
    Configure the Ollama client with custom host and port.
    
    Args:
        host: Hostname or IP address where Ollama is running
        port: Port on which Ollama is listening
        
    Returns:
        None
    """
    ollama.host = f"http://{host}:{port}"
    logger.info(f"Configured Ollama client to use host: {ollama.host}")

def validate_youtube_id(youtube_id: str) -> bool:
    """
    Validates if a string is a properly formatted YouTube ID.
    
    Args:
        youtube_id: The YouTube ID to validate
        
    Returns:
        True if valid YouTube ID format, False otherwise
    """
    if not youtube_id:
        return False
    
    # YouTube IDs are 11 characters long and contain only alphanumeric chars, underscores and hyphens
    return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', youtube_id))

def validate_processing_time(processing_time: float) -> float:
    """
    Validates and corrects processing time to ensure realistic values.
    
    Args:
        processing_time: The processing time in seconds
        
    Returns:
        A realistic processing time value
    """
    # Maximum reasonable processing time (30 minutes)
    MAX_REASONABLE_TIME = 30 * 60
    
    # If processing time is unrealistically high, cap it at a reasonable value
    if processing_time is None or processing_time < 0:
        return 0.0
    elif processing_time > MAX_REASONABLE_TIME:
        logger.warning(f"Unrealistic processing time detected: {processing_time} seconds. Capping at {MAX_REASONABLE_TIME} seconds.")
        return float(MAX_REASONABLE_TIME)
    
    return float(processing_time)

def format_metadata(youtube_id: str, processed_time: Optional[str] = None, 
                   processing_time: Optional[float] = None) -> str:
    """
    Format metadata about video processing into a clean string with validated values.
    Uses the app's database timestamps, not the video's original timestamp.
    
    Args:
        youtube_id: YouTube video ID
        processed_time: When the video was processed by our app (timestamp from database)
        processing_time: How long our processing took in seconds
        
    Returns:
        Formatted metadata string with validated values
    """
    # Validate YouTube ID
    if not validate_youtube_id(youtube_id):
        youtube_id = "Invalid ID"
    
    # Format the processed time using the database timestamp
    now = datetime.datetime.now()
    if processed_time:
        try:
            # Try to parse the string into a datetime
            dt = datetime.datetime.fromisoformat(processed_time.replace('Z', '+00:00'))
            # Ensure we're not showing future dates
            if dt > now:
                dt = now
            processed_time = dt.strftime("%B %d, %Y %I:%M %p")
        except (ValueError, TypeError):
            # If parsing fails, use current time
            processed_time = now.strftime("%B %d, %Y %I:%M %p")
    else:
        processed_time = now.strftime("%B %d, %Y %I:%M %p")
    
    # Validate and format processing time
    if processing_time is not None:
        valid_time = validate_processing_time(processing_time)
        processing_time_str = f"{valid_time:.2f}"
    else:
        processing_time_str = "N/A"
    
    return f"YouTube ID: {youtube_id}\nProcessed: {processed_time}\nProcessing Time: {processing_time_str} seconds"

def is_ollama_available(host=DEFAULT_OLLAMA_HOST, port=DEFAULT_OLLAMA_PORT) -> bool:
    """
    Check if Ollama service is available by trying to connect to its default port.
    
    Args:
        host: Hostname or IP where Ollama is running
        port: Port on which Ollama is listening
        
    Returns:
        bool: True if Ollama appears to be available, False otherwise
    """
    try:
        # Configure Ollama to use the specified host/port
        configure_ollama(host, port)
        
        # Try to ping the Ollama service
        models = ollama.list()
        if models:
            return True
    except (ConnectionRefusedError, socket.error) as e:
        logger.warning(f"Ollama connection failed at {host}:{port}: {str(e)}")
    except Exception as e:
        logger.warning(f"Unexpected error checking Ollama availability at {host}:{port}: {str(e)}")
    
    return False

def get_mistral_summary(text: str, max_length: int = 25000, host=DEFAULT_OLLAMA_HOST, port=DEFAULT_OLLAMA_PORT) -> Optional[str]:
    """
    Generate a summary of the given text using the Ollama Mistral model.
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model (to avoid token limits)
        host: Hostname or IP where Ollama is running
        port: Port on which Ollama is listening
        
    Returns:
        A summary of the text, or None if an error occurred
    """
    start_time = time.time()
    
    # Configure Ollama with the specified host/port
    configure_ollama(host, port)
    logger.info(f"Using Ollama at {host}:{port}")
    
    # First check if Ollama is actually available
    if not is_ollama_available(host, port):
        logger.error(f"Ollama service is not available at {host}:{port}")
        return None
    
    try:
        # Trim text if needed to avoid exceeding token limits
        # 25000 characters is a safe estimate well within Mistral's context window
        if len(text) > max_length:
            # Get the first portion and the last portion to preserve context
            first_part = text[:int(max_length * 0.8)]
            last_part = text[-int(max_length * 0.2):]
            text = first_part + "\n...[content in the middle omitted for length]...\n" + last_part
            logger.info(f"Trimmed text from {len(text)} characters to fit within token limits")
            
        # Construct a prompt for summarization
        prompt = f"""
        You are a video summarization expert. Your task is to summarize the content of a video transcript.
        Please provide a concise summary of the following transcript.
        The summary should be structured and easy to read.
        The summary should be in English and should not include any personal opinions or interpretations.
        The summary should be suitable for someone who has not watched the video.
        Please include:
        1. The main topic and purpose of the video
        2. Key points and arguments presented
        3. Key people, places or organizations mentioned
        4. Important facts, statistics, or examples mentioned
        5. Any conclusions or takeaways
        6. The overall structure of the presentation
        7. Timestamps for major topic transitions (if apparent from the transcript)

        Format the summary in clear paragraphs with appropriate headings for each section. 
        Keep the summary concise but include all essential information. 
        Aim for approximately 200-300 words depending on the video length and complexity.
        If the transcript appears to be truncated, summarize what is available:
        
        {text}
        
        Summary:
        """
        
        # Check if we're running in a container/Railway environment
        is_railway = bool(os.getenv('USE_OLLAMA_REMOTE'))
        
        # Different model preferences based on environment
        if is_railway:
            # For Railway, prefer the smaller quantized model
            model_candidates = ['mistral:7b-instruct-q4_0', 'mistral:7b-instruct-q4_K_M', 'mistral:7b-instruct', 'mistral']
            logger.info("Using Railway deployment model preferences")
        else:
            # For local development, prefer Mistral 3.1
            model_candidates = ['mistral:3.1', 'mistral:7b-instruct', 'mistral:latest', 'mistral-small', 'mistral-small:22b', 'mistral']
            logger.info("Using local development model preferences")
        
        # Check if any of the specified models exists
        try:
            models = ollama.list()
            models_data = models.get('models', [])
            available_models = [model.get('name') for model in models_data]
            logger.info(f"Available Ollama models: {available_models}")
            
            # Find the first available model from our candidates
            model_name = None
            for candidate in model_candidates:
                if candidate in available_models:
                    model_name = candidate
                    logger.info(f"Using model: {model_name}")
                    break
                
            # If no suitable model was found
            if not model_name:
                logger.error(f"No Mistral model found. Available models: {available_models}")
                return None
                
        except Exception as e:
            logger.warning(f"Error checking available models: {str(e)}")
            # Default to first model in our preference list as a best effort
            model_name = model_candidates[0]
            logger.warning(f"Defaulting to model: {model_name}")
        
        # Call the Ollama API with the mistral model
        logger.info(f"Sending request to Ollama with model: {model_name}")
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.2,
                'num_predict': 1024,  # Increased to allow for more comprehensive summaries
            }
        )
        
        # Extract the summary from the response
        if response and 'message' in response and 'content' in response['message']:
            elapsed = time.time() - start_time
            logger.info(f"Successfully generated summary with Ollama using {model_name} in {elapsed:.2f} seconds")
            return response['message']['content'].strip()
        else:
            logger.error(f"Unexpected response format from Ollama: {response}")
            return None
    except (ConnectionRefusedError, socket.error) as e:
        elapsed = time.time() - start_time
        logger.error(f"Error connecting to Ollama service at {host}:{port} after {elapsed:.2f} seconds: {str(e)}")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error generating summary with Ollama after {elapsed:.2f} seconds: {str(e)}")
        return None