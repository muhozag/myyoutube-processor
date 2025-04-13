"""
AI utilities module for interacting with Ollama models.
"""
import logging
import ollama
import re
import datetime
import time
import socket
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

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
    Check if Ollama service is available by trying to connect to its default port.
    
    Returns:
        bool: True if Ollama appears to be available, False otherwise
    """
    try:
        # Try to ping the Ollama service
        models = ollama.list()
        if models:
            return True
    except (ConnectionRefusedError, socket.error) as e:
        logger.warning(f"Ollama connection failed: {str(e)}")
    except Exception as e:
        logger.warning(f"Unexpected error checking Ollama availability: {str(e)}")
    
    return False

def get_mistral_summary(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate a summary of the given text using the Ollama Mistral 22B model.
    
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
        
        # Use mistral-small:22b model as specified for local development
        model_name = 'mistral-small:22b'
        logger.info(f"Using Ollama with model: {model_name}")
        
        # Check if the specified model exists
        try:
            models = ollama.list()
            models_data = models.get('models', [])
            model_names = [model.get('name') for model in models_data]
            
            if model_name not in model_names:
                logger.error(f"Model {model_name} not found in Ollama. Available models: {model_names}")
                # Try with mistral:latest as fallback
                if 'mistral:latest' in model_names:
                    model_name = 'mistral:latest'
                    logger.info(f"Falling back to {model_name}")
                elif 'mistral' in model_names:
                    model_name = 'mistral'
                    logger.info(f"Falling back to {model_name}")
                else:
                    available_models = ", ".join(model_names)
                    logger.error(f"No Mistral model found. Available models: {available_models}")
                    return None
        except Exception as e:
            logger.warning(f"Error checking available models: {str(e)}")
            # Continue with the original model name as a best effort
            pass
        
        # Call the Ollama API with the mistral model
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