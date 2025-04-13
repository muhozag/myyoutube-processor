"""
AI utilities module for interacting with Mistral API models.
"""
import logging
import re
import datetime
import os
import time
import requests
from typing import Optional, Dict, Any, Tuple

# Update to the new Mistral client
from mistralai.async_client import MistralAsyncClient
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

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

def get_mistral_summary_with_requests(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate a summary of the given text using the Mistral API with direct HTTP requests.
    This method uses requests library instead of the official client for Railway compatibility.
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model (to avoid token limits)
        
    Returns:
        A summary of the text, or None if an error occurred
    """
    start_time = time.time()
    try:
        # Get API key from environment
        api_key = os.getenv('MISTRAL_API_KEY')
        
        # Add debug logging to check if API key exists
        logger.info(f"Mistral API key found: {'Yes' if api_key else 'No'}")
        if not api_key:
            logger.error("Mistral API key not found in environment variables")
            return None
            
        # Define headers and endpoint
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        endpoint = "https://api.mistral.ai/v1/chat/completions"
        logger.info("Prepared HTTP request for Mistral API")
        
        # Trim text if needed to avoid exceeding token limits
        if len(text) > max_length:
            # Get the first portion and the last portion to preserve context
            first_part = text[:int(max_length * 0.8)]
            last_part = text[-int(max_length * 0.2):]
            text = first_part + "\n...[content in the middle omitted for length]...\n" + last_part
            logger.info(f"Trimmed text from {len(text)} characters to fit within token limits")
            
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
        
        # Prepare the request payload
        data = {
            "model": "mistral-small-3.1",  # Use mistral-small-3.1 for API calls
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1024
        }
        
        try:
            logger.info("Sending request to Mistral API")
            
            # Make the POST request to the API endpoint
            response = requests.post(endpoint, json=data, headers=headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                logger.info(f"Received successful response from Mistral API, status code: {response.status_code}")
                
                # Parse the JSON response
                json_response = response.json()
                
                # Extract content from the response
                if json_response and "choices" in json_response and len(json_response["choices"]) > 0:
                    summary_content = json_response["choices"][0]["message"]["content"]
                    if summary_content:
                        elapsed = time.time() - start_time
                        logger.info(f"Successfully extracted content from response in {elapsed:.2f} seconds")
                        return summary_content.strip()
                    else:
                        logger.warning("Empty content received from Mistral API")
                else:
                    logger.warning(f"Unexpected response format from Mistral API: {str(json_response)}")
            else:
                logger.error(f"Mistral API request failed with status code {response.status_code}: {response.text}")
            
            return None
            
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return None
            
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error generating summary with Mistral API after {elapsed:.2f} seconds: {str(e)}")
        return None

def get_mistral_summary(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate a summary of the given text using the Mistral API.
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model (to avoid token limits)
        
    Returns:
        A summary of the text, or None if an error occurred
    """
    start_time = time.time()
    
    # Try with requests-based implementation first as it's more reliable on Railway
    logger.info("Starting with requests-based Mistral API implementation for reliability")
    requests_summary = get_mistral_summary_with_requests(text, max_length)
    if requests_summary:
        elapsed = time.time() - start_time
        logger.info(f"Successfully generated summary with requests-based Mistral API in {elapsed:.2f} seconds")
        return requests_summary
    
    # If requests implementation fails, try the official client as fallback
    try:
        # Get API key from environment
        api_key = os.getenv('MISTRAL_API_KEY')
        
        # Add debug logging to check if API key exists
        logger.info(f"Mistral API key found: {'Yes' if api_key else 'No'}")
        if not api_key:
            logger.error("Mistral API key not found in environment variables")
            return None
            
        # Initialize Mistral client
        client = MistralClient(api_key=api_key)
        logger.info("Successfully initialized Mistral client")
        
        # Trim text if needed to avoid exceeding token limits
        if len(text) > max_length:
            # Get the first portion and the last portion to preserve context
            first_part = text[:int(max_length * 0.8)]
            last_part = text[-int(max_length * 0.2):]
            text = first_part + "\n...[content in the middle omitted for length]...\n" + last_part
            logger.info(f"Trimmed text from {len(text)} characters to fit within token limits")
            
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
        
        # Create messages for the API call
        messages = [
            ChatMessage(role="user", content=prompt)
        ]
        
        # Use mistral-small-3.1 model for API calls
        model_name = "mistral-small-3.1"
        
        try:
            logger.info(f"Using Mistral API with model: {model_name}")
            
            # Make the API call
            chat_response = client.chat(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=1024
            )
            
            logger.info(f"Received response from Mistral API with model {model_name}, status: Success")
            
            # Extract content from the response
            if chat_response and chat_response.choices and len(chat_response.choices) > 0:
                summary_content = chat_response.choices[0].message.content
                if summary_content:
                    elapsed = time.time() - start_time
                    logger.info(f"Successfully extracted content from response in {elapsed:.2f} seconds")
                    return summary_content.strip()
                else:
                    logger.warning("Empty content received from Mistral API")
            else:
                logger.warning(f"Unexpected response format from model {model_name}: {str(chat_response)}")
            
            return None
            
        except Exception as e:
            logger.error(f"API call with model {model_name} failed: {str(e)}")
            return None
            
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error generating summary with Mistral API after {elapsed:.2f} seconds: {str(e)}")
        return None