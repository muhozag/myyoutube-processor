"""
AI utilities module for interacting with Mistral API models.
"""
import logging
import re
import datetime
import os
from typing import Optional, Dict, Any, Tuple

# Import only the client class, which should be stable across versions
from mistralai.client import MistralClient

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

def get_mistral_summary(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate a summary of the given text using the Mistral API.
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model (to avoid token limits)
        
    Returns:
        A summary of the text, or None if an error occurred
    """
    try:
        # Get API key from environment
        api_key = os.getenv('MISTRAL_API_KEY')
        if not api_key:
            logger.error("Mistral API key not found in environment variables")
            return None
            
        # Initialize Mistral client
        client = MistralClient(api_key=api_key)
        
        # Trim text if needed to avoid exceeding token limits
        if len(text) > max_length:
            # Get the first portion and the last portion to preserve context
            first_part = text[:int(max_length * 0.8)]
            last_part = text[-int(max_length * 0.2):]
            text = first_part + "\n...[content in the middle omitted for length]...\n" + last_part
            
        # Construct a prompt for summarization (same as Ollama to maintain consistency)
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
        
        # Use simple dictionary format for messages which works with all API versions
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            # Try with mistral-small-latest first
            model_name = "mistral-small-latest"
            logger.info(f"Calling Mistral API with model: {model_name}")
            
            response = client.chat(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=1024
            )
            
            # Extract content from response
            if hasattr(response, 'choices') and len(response.choices) > 0:
                if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'content'):
                    return response.choices[0].message.content.strip()
            
            # If we get here, try to access response as dictionary
            if isinstance(response, dict) and 'choices' in response:
                if len(response['choices']) > 0 and 'message' in response['choices'][0]:
                    return response['choices'][0]['message']['content'].strip()
                    
            logger.warning(f"Unexpected response format: {response}")
            return None
            
        except Exception as e:
            # Fall back to a different model name if the first one fails
            logger.warning(f"First API call failed: {str(e)}. Trying fallback model.")
            
            try:
                # Try with mistral-small (without -latest)
                model_name = "mistral-small"
                logger.info(f"Calling Mistral API with fallback model: {model_name}")
                
                response = client.chat(
                    model=model_name,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1024
                )
                
                # Extract content using the same approach
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'content'):
                        return response.choices[0].message.content.strip()
                
                # If we get here, try to access response as dictionary
                if isinstance(response, dict) and 'choices' in response:
                    if len(response['choices']) > 0 and 'message' in response['choices'][0]:
                        return response['choices'][0]['message']['content'].strip()
                
                logger.warning(f"Unexpected response format from fallback: {response}")
                return None
                
            except Exception as e2:
                logger.error(f"Both API call attempts failed. Final error: {str(e2)}")
                return None
                
    except Exception as e:
        logger.error(f"Error generating summary with Mistral API: {str(e)}")
        return None