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
import requests
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Get Ollama host from environment variable with default to localhost
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
# Get API key for VPS authentication if needed
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY', '')

# Configure Ollama client to use the specified host
if OLLAMA_HOST and OLLAMA_HOST != 'http://localhost:11434':
    logger.info(f"Configuring Ollama to use remote host: {OLLAMA_HOST}")
    # Set the Ollama API base URL
    ollama.host = OLLAMA_HOST

# Default model for local development (larger model)
LOCAL_MODEL = os.getenv('OLLAMA_LOCAL_MODEL', 'mistral-small:22b')

# Model to use on your VPS - now configurable via env var
VPS_MODEL = os.getenv('OLLAMA_VPS_MODEL', 'mistral:7b')

# Smaller model for Railway deployment to fit within standard resources
RAILWAY_MODEL = os.getenv('OLLAMA_RAILWAY_MODEL', 'mistral:7b')

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

def is_ollama_available() -> bool:
    """
    Check if Ollama service is available by trying to connect to its endpoint.
    Works with both local and remote Ollama instances.
    
    Returns:
        bool: True if Ollama appears to be available, False otherwise
    """
    try:
        # Check if Ollama API is accessible
        if not OLLAMA_HOST.startswith(('http://', 'https://')):
            url = f"http://{OLLAMA_HOST}/api/tags"
        else:
            url = f"{OLLAMA_HOST}/api/tags"
            
        logger.info(f"Checking Ollama availability at: {url}")
        
        # Add detailed error handling for connection issues
        try:
            # Add simple check if remote host is available
            headers = {}
            if OLLAMA_API_KEY:
                headers['Authorization'] = f'Bearer {OLLAMA_API_KEY}'
                
            response = requests.get(url, headers=headers, timeout=15)  # Increased timeout for slower networks
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name') for model in models if 'name' in model]
                logger.info(f"Ollama service is available with models: {', '.join(model_names) if model_names else 'No models found'}")
                
                # Check if our models are available
                if running_in_railway_env():
                    if not any(model.lower().startswith(RAILWAY_MODEL.split(':')[0].lower()) for model in model_names):
                        logger.warning(f"Required Railway model {RAILWAY_MODEL} not found on Ollama server")
                        logger.info(f"Available models: {', '.join(model_names)}")
                        return False
                elif use_vps_model():
                    if not any(model.lower().startswith(VPS_MODEL.split(':')[0].lower()) for model in model_names):
                        logger.warning(f"Required VPS model {VPS_MODEL} not found on Ollama server")
                        logger.info(f"Available models: {', '.join(model_names)}")
                        return False
                else:
                    if not any(model.lower().startswith(LOCAL_MODEL.split(':')[0].lower()) for model in model_names):
                        logger.warning(f"Required local model {LOCAL_MODEL} not found on Ollama server")
                        logger.info(f"Available models: {', '.join(model_names)}")
                        return False
                
                return True
            else:
                logger.warning(f"Ollama service returned status code {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.ConnectTimeout:
            logger.warning(f"Connection to Ollama at {url} timed out after 15 seconds")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error to Ollama at {url}: {str(e)}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error to Ollama at {url}: {str(e)}")
            return False
            
    except Exception as e:
        logger.warning(f"Unexpected error checking Ollama availability: {str(e)}")
    
    return False

def running_in_railway_env() -> bool:
    """
    Detect if code is running in Railway environment.
    Helper function for use within ollama_utils.py
    
    Returns:
        True if running on Railway, False otherwise
    """
    return bool(os.getenv('RAILWAY_ENVIRONMENT') or 
                os.getenv('RAILWAY_PROJECT_ID') or 
                os.getenv('RAILWAY_SERVICE_ID'))

def is_railway_environment() -> bool:
    """
    Detect if code is running in Railway environment.
    
    Returns:
        True if running on Railway, False otherwise
    """
    return bool(os.getenv('RAILWAY_ENVIRONMENT') or 
                os.getenv('RAILWAY_PROJECT_ID') or 
                os.getenv('RAILWAY_SERVICE_ID'))

def use_vps_model() -> bool:
    """
    Determine if we should use the VPS model based on configuration.
    
    Returns:
        True if VPS model should be used, False otherwise
    """
    # If OLLAMA_HOST points to a non-localhost address and USE_VPS_MODEL is set to true
    use_vps = os.getenv('USE_VPS_MODEL', 'false').lower() in ('true', 'yes', '1', 't')
    remote_host = OLLAMA_HOST != 'http://localhost:11434'
    
    return use_vps and remote_host

def get_mistral_summary(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate a summary of the given text using Ollama models.
    Uses a smaller model on Railway and a larger model locally,
    or connects to a VPS-hosted Ollama if configured.
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model (to avoid token limits)
        
    Returns:
        A summary of the text, or None if an error occurred
    """
    start_time = time.time()
    
    # First check if Ollama is actually available
    if not is_ollama_available():
        logger.error("Ollama service is not available")
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
        
        # Choose model based on environment and configuration
        if use_vps_model():
            model_name = VPS_MODEL
            logger.info(f"Using VPS-hosted model: {model_name}")
        elif is_railway_environment():
            model_name = RAILWAY_MODEL
            logger.info(f"Railway environment detected - using smaller model: {model_name}")
        else:
            model_name = LOCAL_MODEL
            logger.info(f"Local environment detected - using larger model: {model_name}")
        
        # Call the Ollama API with the selected model
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
            logger.info(f"Successfully generated summary with Ollama in {elapsed:.2f} seconds")
            return response['message']['content'].strip()
        else:
            logger.error(f"Unexpected response format from Ollama: {response}")
            return None
    except (ConnectionRefusedError, socket.error) as e:
        elapsed = time.time() - start_time
        logger.error(f"Error connecting to Ollama service after {elapsed:.2f} seconds: {str(e)}")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error generating summary with Ollama after {elapsed:.2f} seconds: {str(e)}")
        return None