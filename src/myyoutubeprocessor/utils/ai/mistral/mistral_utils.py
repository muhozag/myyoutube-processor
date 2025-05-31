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
    Generate a summary using the Mistral API client with improved language support.
    
    Args:
        text: The text to summarize
        max_length: Maximum length of text to send to the model (default: 25000)
        
    Returns:
        The generated summary, or None if generation failed
    """
    if not text or not text.strip():
        logger.warning("Empty or whitespace-only text provided for summarization")
        return None
        
    start_time = time.time()
    
    try:
        # Get the API key
        api_key = os.environ.get('MISTRAL_API_KEY')
        if not api_key:
            logger.error("MISTRAL_API_KEY environment variable not set")
            return None
        
        # Initialize the client
        client = Mistral(api_key=api_key)
        
        # Trim text if it's too long
        if len(text) > max_length:
            # Get the first 80% and last 20% to preserve context
            first_part = text[:int(max_length * 0.8)]
            last_part = text[-int(max_length * 0.2):]
            text = first_part + "\n...[content in the middle omitted for length]...\n" + last_part
            logger.info(f"Trimmed text to {len(text)} characters for Mistral API")
        
        # Detect if the content appears to be in a non-English language
        # Simple heuristic: if the text contains non-Latin characters, it might be non-English
        non_latin_chars = sum(1 for char in text[:500] if not char.isascii() and char.isalpha())
        total_alpha_chars = sum(1 for char in text[:500] if char.isalpha())
        
        is_likely_non_english = False
        if total_alpha_chars > 0:
            non_latin_ratio = non_latin_chars / total_alpha_chars
            is_likely_non_english = non_latin_ratio > 0.3  # More than 30% non-Latin characters
        
        # Construct a language-aware prompt for summarization
        if is_likely_non_english:
            prompt = f"""
        You are a multilingual video summarization expert. Your task is to summarize the content of a video transcript that appears to be in a non-English language.
        
        Please provide a comprehensive summary of the following transcript.
        
        IMPORTANT INSTRUCTIONS:
        1. If the transcript is in a language other than English (such as Amharic, Arabic, Chinese, etc.), provide the summary in ENGLISH
        2. Identify the language of the original transcript at the beginning of your summary
        3. Do not hallucinate or invent any information that is not present in the transcript
        4. Only include facts, topics, and information that are explicitly stated in the provided text
        5. If something is unclear or ambiguous in the transcript, note that uncertainty rather than making assumptions
        6. If you're unsure about any detail, omit it rather than potentially providing incorrect information
        7. Preserve the meaning and context while translating concepts to English
        
        Please include in your English summary:
        1. The detected language of the original transcript
        2. The main topic and purpose of the video
        3. Key points and arguments presented
        4. Key people, places or organizations mentioned
        5. Important facts, statistics, or examples mentioned
        6. Any conclusions or takeaways
        7. The overall structure of the presentation
        8. Timestamps for major topic transitions (if apparent from the transcript)
        
        Format the summary in clear paragraphs with appropriate headings for each section. 
        Keep the summary concise but include all essential information. 
        Aim for approximately 300-500 words depending on the video length and complexity.
        If the transcript appears to be truncated, summarize what is available and note the limitation.
        
        Transcript to summarize:
        
        {text}
        
        Summary in English:
        """
        else:
            # Standard English prompt
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
            
            # Extract the response content
            if chat_response and chat_response.choices and len(chat_response.choices) > 0:
                summary = chat_response.choices[0].message.content.strip()
                elapsed = time.time() - start_time
                logger.info(f"Successfully generated summary with Mistral API in {elapsed:.2f} seconds")
                return summary
            else:
                logger.error("Unexpected response format from Mistral API")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Mistral API: {str(e)}")
            return None
            
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error generating summary with Mistral API after {elapsed:.2f} seconds: {str(e)}")
        return None