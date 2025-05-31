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
else:
    # For local development, check if IPv6 is preferred
    try:
        # Try IPv6 connection
        session = requests.Session()
        ipv6_url = "http://[::1]:11434/api/tags"
        response = session.get(ipv6_url, timeout=2)
        if response.status_code == 200:
            logger.info("IPv6 connection successful, configuring Ollama to use [::1]")
            ollama.host = "http://[::1]:11434"
        else:
            logger.info("Using default IPv4 Ollama connection")
    except requests.exceptions.RequestException:
        logger.info("IPv6 connection failed, using default IPv4 Ollama connection")
        # Just use the default (IPv4)

# Default model for local development (larger model)
LOCAL_MODEL = os.getenv('OLLAMA_LOCAL_MODEL', 'mistral-small:22b')

# Model to use on your VPS - now configurable via env var
VPS_MODEL = os.getenv('OLLAMA_VPS_MODEL', 'mistral-small:22b')

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
    Supports both IPv4 and IPv6 connections.
    
    Returns:
        bool: True if Ollama appears to be available, False otherwise
    """
    try:
        # Extract the host from OLLAMA_HOST
        host_url = OLLAMA_HOST
        if not host_url.startswith(('http://', 'https://')):
            url = f"http://{host_url}/api/tags"
        else:
            url = f"{host_url}/api/tags"
            
        logger.info(f"Checking Ollama availability at: {url}")
        
        # Add detailed error handling for connection issues
        try:
            # Set up headers if API key is provided
            headers = {}
            if OLLAMA_API_KEY:
                headers['Authorization'] = f'Bearer {OLLAMA_API_KEY}'
                
            # Print connection information for debugging (without exposing the API key)
            logger.debug(f"Connecting to Ollama with: URL={url}, Headers={'Using auth' if OLLAMA_API_KEY else 'No auth'}")
            
            # Configure requests to handle both IPv4 and IPv6
            session = requests.Session()
            # Force IPv6 if we're connecting to localhost and IPv6 is likely being used
            if 'localhost' in host_url or '127.0.0.1' in host_url:
                # Try to connect via IPv6 localhost
                ipv6_url = url.replace('localhost', '[::1]').replace('127.0.0.1', '[::1]')
                logger.info(f"Trying IPv6 connection: {ipv6_url}")
                try:
                    response = session.get(ipv6_url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        logger.info("Successfully connected via IPv6")
                        url = ipv6_url  # Use IPv6 URL for subsequent operations
                    else:
                        # Fall back to the original URL (IPv4)
                        logger.info(f"IPv6 connection failed with status {response.status_code}, falling back to IPv4")
                        response = session.get(url, headers=headers, timeout=5)
                except requests.exceptions.RequestException:
                    # Fall back to the original URL (IPv4)
                    logger.info("IPv6 connection failed, falling back to IPv4")
                    response = session.get(url, headers=headers, timeout=5)
            else:
                # For non-localhost URLs, just use the provided URL
                response = session.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name') for model in models if 'name' in model]
                logger.info(f"Ollama service is available with models: {', '.join(model_names) if model_names else 'No models found'}")
                
                # Check if our models are available
                if not any(model.lower().startswith(LOCAL_MODEL.split(':')[0].lower()) for model in model_names):
                    logger.warning(f"Required local model {LOCAL_MODEL} not found on Ollama server")
                    logger.info(f"Available models: {', '.join(model_names)}")
                    return False
                
                return True
            else:
                logger.warning(f"Ollama service returned status code {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.ConnectTimeout:
            logger.warning(f"Connection to Ollama at {url} timed out after 5 seconds")
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

def get_mistral_summary(text: str, max_length: int = 32000) -> Optional[str]:
    """
    Generate a summary using Mistral AI via API or local Ollama instance.
    Enhanced with better foreign language support and detection.
    
    Args:
        text (str): The text to summarize
        max_length (int): Maximum text length to process (default: 32000 characters)
        
    Returns:
        Optional[str]: Generated summary or None if failed
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for summarization")
        return None
        
    try:
        # Note: This is a very conservative estimate of 4 chars per token
        # and the non vps model should take up to take up to 32000 tokens
        if not use_vps_model() and len(text) > max_length:
            # Get the first portion and the last portion to preserve context
            first_part = text[:int(max_length * 0.8)]
            last_part = text[-int(max_length * 0.2):]
            text = first_part + "\n...[content in the middle omitted for length]...\n" + last_part
            logger.info(f"Trimmed text from {len(text)} characters to fit within token limits")
            
        # Enhanced language detection for better foreign language support
        detected_language, confidence = detect_text_language(text)
        is_likely_non_english = detected_language != 'en' and confidence > 0.5
        
        logger.info(f"Detected language: {detected_language} (confidence: {confidence:.2f})")
        
        # Language-specific prompting for better multilingual support
        if is_likely_non_english:
            prompt = f"""
            You are a multilingual video summarization expert. Your task is to summarize the content of a video transcript that appears to be in {get_language_name(detected_language)}.
            
            Please provide a comprehensive summary of the following transcript.
            
            IMPORTANT INSTRUCTIONS:
            1. Provide the summary in ENGLISH, regardless of the original language
            2. Begin your summary by identifying the original language: "This video is in {get_language_name(detected_language)}."
            3. Do not hallucinate or invent any information that is not present in the transcript
            4. Only include facts, topics, and information that are explicitly stated in the provided text
            5. If something is unclear or ambiguous in the transcript, note that uncertainty rather than making assumptions
            6. If you're unsure about any detail, omit it rather than potentially providing incorrect information
            7. Preserve the meaning and context while translating concepts to English
            8. Maintain cultural context and proper nouns in their original form when appropriate
            
            Please include in your English summary:
            1. The main topic and purpose of the video
            2. Key points and arguments presented
            3. Important people, places, organizations, or concepts mentioned
            4. Any conclusions or calls to action
            5. The overall tone and style of the content
            
            If the transcript contains technical terms, cultural references, or concepts that don't translate directly to English, please provide brief explanations in parentheses.
            
            Transcript to summarize:
            
            {text}
            
            Please provide your summary in English:
            """
        else:
            # Standard English prompting
            prompt = f"""
            You are a professional video content summarization expert. Your task is to create a comprehensive summary of the following video transcript.
            
            IMPORTANT INSTRUCTIONS:
            1. Do not hallucinate or invent any information that is not present in the transcript
            2. Only include facts, topics, and information that are explicitly stated in the provided text
            3. If something is unclear or ambiguous in the transcript, note that uncertainty rather than making assumptions
            4. If you're unsure about any detail, omit it rather than potentially providing incorrect information
            5. Be accurate and factual in your summary
            
            Please include in your summary:
            1. The main topic and purpose of the video
            2. Key points and arguments presented
            3. Important people, places, organizations, or concepts mentioned
            4. Any conclusions or calls to action
            5. The overall tone and style of the content
            
            Transcript to summarize:
            
            {text}
            
            Please provide your summary:
            """
        
        # Try VPS model first if configured
        if use_vps_model():
            logger.info("Attempting summary generation using VPS Mistral model")
            try:
                summary = get_vps_mistral_summary(prompt)
                if summary:
                    logger.info(f"Successfully generated summary using VPS model (language: {detected_language})")
                    return summary
                else:
                    logger.warning("VPS model returned empty summary, falling back to other methods")
            except Exception as e:
                logger.warning(f"VPS model failed: {str(e)}, falling back to other methods")
        
        # Try Mistral API if configured
        mistral_api_key = os.environ.get('MISTRAL_API_KEY')
        if mistral_api_key:
            logger.info("Attempting summary generation using Mistral API")
            try:
                summary = get_mistral_api_summary(prompt, mistral_api_key)
                if summary:
                    logger.info(f"Successfully generated summary using Mistral API (language: {detected_language})")
                    return summary
                else:
                    logger.warning("Mistral API returned empty summary, falling back to local Ollama")
            except Exception as e:
                logger.warning(f"Mistral API failed: {str(e)}, falling back to local Ollama")
        
        # Finally try local Ollama
        if is_ollama_available():
            logger.info("Attempting summary generation using local Ollama")
            try:
                summary = get_ollama_summary(prompt)
                if summary:
                    logger.info(f"Successfully generated summary using local Ollama (language: {detected_language})")
                    return summary
                else:
                    logger.warning("Local Ollama returned empty summary")
            except Exception as e:
                logger.error(f"Local Ollama failed: {str(e)}")
        
        logger.error("All summarization methods failed")
        return None
        
    except Exception as e:
        logger.error(f"Error in get_mistral_summary: {str(e)}", exc_info=True)
        return None


def detect_text_language(text: str, sample_size: int = 1000) -> tuple[str, float]:
    """
    Detect the language of the input text with improved accuracy for various scripts.
    
    Args:
        text (str): Text to analyze
        sample_size (int): Number of characters to sample for analysis
        
    Returns:
        tuple[str, float]: (language_code, confidence) where confidence is 0.0-1.0
    """
    if not text or len(text.strip()) < 10:
        return 'en', 0.0
    
    # Use a sample for better performance on long texts
    sample_text = text[:sample_size] if len(text) > sample_size else text
    
    try:
        # Try langdetect library if available
        try:
            from langdetect import detect, detect_langs
            detected = detect(sample_text)
            
            # Get confidence score
            lang_probs = detect_langs(sample_text)
            confidence = max([lang.prob for lang in lang_probs if lang.lang == detected], default=0.0)
            
            return detected, confidence
        except ImportError:
            pass
    except:
        pass
    
    # Fallback: simple heuristic-based detection
    # Count different script types
    latin_chars = sum(1 for char in sample_text if char.isalpha() and ord(char) < 256)
    arabic_chars = sum(1 for char in sample_text if '\u0600' <= char <= '\u06FF')
    chinese_chars = sum(1 for char in sample_text if '\u4e00' <= char <= '\u9fff')
    cyrillic_chars = sum(1 for char in sample_text if '\u0400' <= char <= '\u04FF')
    devanagari_chars = sum(1 for char in sample_text if '\u0900' <= char <= '\u097F')
    ethiopic_chars = sum(1 for char in sample_text if '\u1200' <= char <= '\u137F')
    
    total_alpha = sum(1 for char in sample_text if char.isalpha())
    
    if total_alpha == 0:
        return 'en', 0.0
    
    # Calculate script ratios
    if ethiopic_chars / total_alpha > 0.3:
        return 'am', 0.8  # Likely Amharic
    elif arabic_chars / total_alpha > 0.3:
        return 'ar', 0.8  # Likely Arabic
    elif chinese_chars / total_alpha > 0.3:
        return 'zh', 0.8  # Likely Chinese
    elif cyrillic_chars / total_alpha > 0.3:
        return 'ru', 0.7  # Likely Russian (or other Cyrillic)
    elif devanagari_chars / total_alpha > 0.3:
        return 'hi', 0.7  # Likely Hindi
    elif latin_chars / total_alpha > 0.8:
        # Could be many languages, need more analysis
        # Simple keyword-based detection for common languages
        text_lower = sample_text.lower()
        
        # Spanish indicators
        if any(word in text_lower for word in ['que', 'con', 'una', 'para', 'como', 'por', 'del', 'las', 'los']):
            return 'es', 0.6
        
        # French indicators  
        elif any(word in text_lower for word in ['que', 'avec', 'pour', 'dans', 'une', 'des', 'les', 'sur', 'est']):
            return 'fr', 0.6
            
        # German indicators
        elif any(word in text_lower for word in ['und', 'der', 'die', 'das', 'ich', 'sie', 'mit', 'auf', 'für']):
            return 'de', 0.6
            
        # Default to English for Latin script
        return 'en', 0.5
    else:
        # Mixed script or unrecognized
        return 'en', 0.3


def get_language_name(language_code: str) -> str:
    """
    Get the full language name from a language code.
    
    Args:
        language_code (str): ISO language code
        
    Returns:
        str: Full language name
    """
    language_names = {
        'am': 'Amharic',
        'ar': 'Arabic', 
        'zh': 'Chinese',
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'hi': 'Hindi',
        'ja': 'Japanese',
        'ko': 'Korean',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'it': 'Italian',
        'tr': 'Turkish',
        'fa': 'Persian/Farsi',
        'ur': 'Urdu',
        'bn': 'Bengali',
        'ta': 'Tamil',
        'te': 'Telugu',
        'th': 'Thai',
        'vi': 'Vietnamese',
        'sw': 'Swahili',
        'rw': 'Kinyarwanda',
        'he': 'Hebrew',
        'ti': 'Tigrinya',
        'om': 'Oromo',
        'so': 'Somali',
        'ha': 'Hausa',
        'yo': 'Yoruba',
        'ig': 'Igbo',
    }
    
    return language_names.get(language_code, f"Language ({language_code})")
def get_current_model_info() -> str:
    """
    Get information about the currently used AI model based on environment and configuration.
    This is used for displaying model information on the transcript page.
    
    Returns:
        str: A user-friendly description of the current AI model being used
    """
    try:
        # Determine the current model based on environment and configuration
        if use_vps_model():
            model_name = VPS_MODEL
            deployment = "VPS-hosted"
        else:
            model_name = LOCAL_MODEL
            deployment = "Local"
        
        # Format the model name to be more user-friendly
        # Convert 'mistral-small:22b' to 'Mistral-small 22B'
        friendly_name = model_name
        
        # Split by colon if present
        parts = model_name.split(':')
        base_model = parts[0].replace('-', ' ').title()
        
        # Format the version if present
        if len(parts) > 1:
            version = parts[1].upper()
            if version.endswith('B'):
                friendly_name = f"{base_model} {version}"
            else:
                friendly_name = f"{base_model} {version}B"
        else:
            friendly_name = base_model
        
        # If using Mistral API rather than Ollama
        mistral_api_key = os.environ.get('MISTRAL_API_KEY')
        if mistral_api_key and not is_ollama_available():
            return f"Mistral Cloud API"
        
        return friendly_name
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        return "Mistral AI"  # Default fallback name

def use_vps_model() -> bool:
    """
    Determine if we should use the VPS model based on environment variables.
    
    Returns:
        True if VPS model should be used, False otherwise
    """
    return os.getenv('USE_VPS_MODEL', 'false').lower() in ('true', 'yes', '1', 't')

def get_vps_mistral_summary(prompt: str) -> Optional[str]:
    """
    Generate summary using VPS-hosted Ollama instance.
    
    Args:
        prompt: The prompt to send to the model
        
    Returns:
        Generated summary or None if failed
    """
    try:
        model = VPS_MODEL
        
        logger.info(f"Using VPS model: {model}")
        
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={
                'temperature': 0.7,
                'num_predict': 2000,
                'top_p': 0.9,
                'repeat_penalty': 1.1,
            }
        )
        
        summary = response.get('response', '').strip()
        if summary:
            logger.info(f"VPS model generated {len(summary)} character summary")
            return summary
        else:
            logger.warning("VPS model returned empty response")
            return None
            
    except Exception as e:
        logger.error(f"Error with VPS Mistral model: {str(e)}")
        return None

def get_ollama_summary(prompt: str) -> Optional[str]:
    """
    Generate summary using local Ollama instance.
    
    Args:
        prompt: The prompt to send to the model
        
    Returns:
        Generated summary or None if failed
    """
    try:
        model = LOCAL_MODEL
        
        logger.info(f"Using local model: {model}")
        
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={
                'temperature': 0.7,
                'num_predict': 2000,
                'top_p': 0.9,
                'repeat_penalty': 1.1,
            }
        )
        
        summary = response.get('response', '').strip()
        if summary:
            logger.info(f"Local model generated {len(summary)} character summary")
            return summary
        else:
            logger.warning("Local model returned empty response")
            return None
            
    except Exception as e:
        logger.error(f"Error with local Ollama model: {str(e)}")
        return None

def get_mistral_api_summary(prompt: str, api_key: str) -> Optional[str]:
    """
    Generate summary using Mistral API.
    
    Args:
        prompt: The prompt to send to the model
        api_key: Mistral API key
        
    Returns:
        Generated summary or None if failed
    """
    try:
        from mistralai.client import MistralClient
        
        client = MistralClient(api_key=api_key)
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = client.chat(
            model="mistral-medium",
            messages=messages,
            max_tokens=2000,
            temperature=0.7,
        )
        
        summary = response.choices[0].message.content.strip()
        if summary:
            logger.info(f"Mistral API generated {len(summary)} character summary")
            return summary
        else:
            logger.warning("Mistral API returned empty response")
            return None
            
    except Exception as e:
        logger.error(f"Error with Mistral API: {str(e)}")
        return None