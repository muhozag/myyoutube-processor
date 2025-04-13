"""
Utility functions for processing YouTube URLs and extracting video IDs.

This module implements regex patterns to extract YouTube video IDs from various URL formats,
including standard videos, shorts, playlists, and URLs with timestamps.
"""

import re
from typing import Optional, Dict, List, Union, Tuple
import logging
import time
import sys
import platform

# Adding requirement for transcript extraction
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
except ImportError:
    logging.warning("youtube_transcript_api not installed. Transcript extraction won't work.")


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.
    
    Args:
        url (str): YouTube URL in various possible formats
        
    Returns:
        Optional[str]: YouTube video ID if found, None otherwise
        
    Examples:
        >>> extract_youtube_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        'dQw4w9WgXcQ'
        >>> extract_youtube_id('https://youtu.be/dQw4w9WgXcQ')
        'dQw4w9WgXcQ'
        >>> extract_youtube_id('https://youtube.com/shorts/dQw4w9WgXcQ')
        'dQw4w9WgXcQ'
    """
    patterns = [
        # Standard YouTube URLs
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})(?:&.*)?',
        # Short YouTube URLs
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})(?:\?.*)?',
        # YouTube Shorts
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})(?:\?.*)?',
        # YouTube URLs with timestamp
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})(?:&.*)?(?:&t=\d+)?',
        # YouTube embedded player
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?:\?.*)?',
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    
    # Handle YouTube playlist URLs that include a video ID
    playlist_pattern = r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})&list=([a-zA-Z0-9_-]+)(?:&.*)?'
    playlist_match = re.match(playlist_pattern, url)
    if playlist_match:
        return playlist_match.group(1)
    
    return None


def is_valid_youtube_id(youtube_id: str) -> bool:
    """
    Validate if a string is a properly formatted YouTube ID.
    
    Args:
        youtube_id (str): String to validate as YouTube ID
        
    Returns:
        bool: True if valid YouTube ID format, False otherwise
    """
    if not youtube_id:
        return False
    
    # YouTube IDs are 11 characters long and contain only alphanumeric chars, underscores and hyphens
    return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', youtube_id))


def extract_transcript(youtube_id: str, language_code: str = 'en', return_raw: bool = False) -> Union[Tuple[str, bool, str], Tuple[str, bool, str, Union[List, Dict, object]]]:
    """
    Extract transcript for a YouTube video using youtube_transcript_api.
    
    Args:
        youtube_id (str): YouTube video ID
        language_code (str): Preferred language code (default: 'en')
        return_raw (bool): Whether to return the raw transcript data along with the formatted text
        
    Returns:
        Union[Tuple[str, bool, str], Tuple[str, bool, str, object]]: 
            - If return_raw=False: (transcript_text, is_auto_generated, language_code)
            - If return_raw=True: (transcript_text, is_auto_generated, language_code, raw_data)
            
    Note:
        If the preferred language is not available, the function will try to get
        any available transcript, preferring manually created ones.
    """
    if not is_valid_youtube_id(youtube_id):
        logging.error(f"Invalid YouTube ID: {youtube_id}")
        return ("", False, "") if not return_raw else ("", False, "", None)
    
    # Verify YouTubeTranscriptApi is available
    if 'YouTubeTranscriptApi' not in globals():
        try:
            global YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
            from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
            logging.info("Successfully imported YouTube Transcript API on demand")
        except ImportError:
            logging.error("youtube_transcript_api not installed. Cannot extract transcript.")
            return ("", False, "") if not return_raw else ("", False, "", None)
    
    try:
        # Enhanced environment logging to help diagnose differences
        env_info = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'youtube_transcript_api_version': getattr(YouTubeTranscriptApi, '__version__', 'unknown')
        }
        logging.info(f"Environment info for transcript extraction: {env_info}")
        
        # Add timeout to the transcript API calls
        start_time = time.time()
        
        # Get a list of all available transcripts
        logging.info(f"Attempting to list all available transcripts for video {youtube_id}")
        transcript_list = YouTubeTranscriptApi.list_transcripts(youtube_id)
        
        available_languages = [t.language_code for t in transcript_list]
        logging.info(f"Available transcript languages for {youtube_id}: {available_languages}")
        
        transcript = None
        transcript_data = None
        is_generated = True
        actual_language = language_code
        
        # Try to get manual transcript in preferred language
        try:
            logging.info(f"Trying to find manual transcript in {language_code}")
            transcript = transcript_list.find_transcript([language_code])
            if not transcript.is_generated:
                logging.info(f"Found manual transcript in {language_code}")
                transcript_data = transcript.fetch()
                is_generated = False
                actual_language = transcript.language_code
        except NoTranscriptFound:
            logging.info(f"No manual transcript found in {language_code}")
            pass
            
        # If no manual transcript, try to get auto-generated transcript in preferred language
        if not transcript_data:
            try:
                logging.info(f"Trying to find auto-generated transcript in {language_code}")
                transcript = transcript_list.find_transcript([language_code])
                transcript_data = transcript.fetch()
                is_generated = transcript.is_generated
                actual_language = transcript.language_code
                logging.info(f"Found auto-generated transcript in {language_code}")
            except NoTranscriptFound:
                logging.info(f"No auto-generated transcript found in {language_code}")
                pass
        
        # If preferred language not found, try any manually created transcript
        if not transcript_data:
            manual_transcripts = [t for t in transcript_list if not t.is_generated]
            if manual_transcripts:
                selected = manual_transcripts[0]
                logging.info(f"Using manual transcript in {selected.language_code} instead of preferred {language_code}")
                transcript_data = selected.fetch()
                is_generated = False
                actual_language = selected.language_code
                
        # Last resort: get any auto-generated transcript
        if not transcript_data:
            logging.info("No manual transcripts found, trying any available transcript")
            
            # Try English first, then try the first available language
            try:
                transcript = transcript_list.find_transcript(['en'])
                logging.info(f"Found English transcript as fallback")
                transcript_data = transcript.fetch()
                is_generated = transcript.is_generated
                actual_language = transcript.language_code
            except NoTranscriptFound:
                # Get the first available transcript from the list
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    transcript = available_transcripts[0]
                    logging.info(f"Using transcript in {transcript.language_code} as last resort")
                    transcript_data = transcript.fetch()
                    is_generated = transcript.is_generated
                    actual_language = transcript.language_code
                else:
                    logging.warning(f"No transcripts found after listing them (unusual situation)")
                    return ("", False, "") if not return_raw else ("", False, "", None)
        
        # Log the time it took to fetch the transcript
        elapsed_time = time.time() - start_time
        logging.info(f"Transcript fetch time: {elapsed_time:.2f} seconds")
        
        # Log detailed info about the transcript data
        logging.info(f"Transcript data type: {type(transcript_data)}")
        if isinstance(transcript_data, list) and transcript_data:
            logging.info(f"First transcript segment: {transcript_data[0]}")
            logging.info(f"Total segments: {len(transcript_data)}")
        elif hasattr(transcript_data, 'text'):
            logging.info(f"Text preview: {transcript_data.text[:50]}...")
        
        # Format the transcript into plain text
        formatted_text = _format_transcript(transcript_data)
        
        if not formatted_text:
            logging.warning(f"Failed to format transcript for video {youtube_id}")
            
        # Check if transcript is empty after formatting
        if not formatted_text.strip():
            logging.warning(f"Transcript for video {youtube_id} is empty after formatting")
        else:
            logging.info(f"Formatted transcript length: {len(formatted_text)} chars, preview: {formatted_text[:50]}...")
            
        # Log completion
        logging.info(f"Successfully extracted transcript for video {youtube_id} in {actual_language}")
        
        if return_raw:
            return formatted_text, is_generated, actual_language, transcript_data
        else:
            return formatted_text, is_generated, actual_language
            
    except TranscriptsDisabled as e:
        logging.warning(f"Transcripts are disabled for video {youtube_id}: {str(e)}")
        return ("", False, "") if not return_raw else ("", False, "", None)
    except NoTranscriptFound as e:
        logging.warning(f"No transcript found for video {youtube_id}: {str(e)}")
        return ("", False, "") if not return_raw else ("", False, "", None)
    except Exception as e:
        logging.error(f"Error extracting transcript for video {youtube_id}: {str(e)}", exc_info=True)
        return ("", False, "") if not return_raw else ("", False, "", None)


def _format_transcript(transcript_data) -> str:
    """
    Format transcript data from YouTubeTranscriptApi into a clean text.
    
    Args:
        transcript_data: Either a list of transcript segment dictionaries 
                        (each with 'text', 'start', 'duration' keys)
                        or a FetchedTranscriptSnippet object or other format
                        
    Returns:
        str: Formatted transcript text
    """
    try:
        # Enhanced logging to diagnose transcript formatting issues
        logging.info(f"Formatting transcript data of type: {type(transcript_data)}")
        
        # Check if transcript_data is a list (traditional API format)
        if isinstance(transcript_data, list):
            if not transcript_data:
                logging.warning("Empty transcript data list")
                return ""
                
            # Log sample from the data to help diagnose issues
            if len(transcript_data) > 0:
                logging.info(f"First transcript segment: {transcript_data[0]}")
                if 'text' not in transcript_data[0]:
                    logging.warning(f"First transcript segment is missing 'text' key. Keys: {transcript_data[0].keys() if hasattr(transcript_data[0], 'keys') else 'no keys method'}")
            
            formatted_text = " ".join(item['text'].strip() for item in transcript_data if 'text' in item)
            logging.info(f"Formatted list transcript with {len(transcript_data)} segments into text of length {len(formatted_text)}")
            return formatted_text
        
        # Handle FetchedTranscriptSnippet object (new API format)
        elif hasattr(transcript_data, 'text'):
            text = transcript_data.text.strip()
            logging.info(f"Extracted text from transcript object with 'text' attribute, length: {len(text)}")
            return text
        
        # For any other format, try different approaches
        else:
            logging.warning(f"Unknown transcript data format type: {type(transcript_data)}")
            
            # Try to convert to dictionary if it's a custom object
            if hasattr(transcript_data, '__dict__'):
                data_dict = transcript_data.__dict__
                logging.info(f"Converted to dict with keys: {list(data_dict.keys())}")
                
                if 'text' in data_dict:
                    return data_dict['text'].strip()
                    
            # If it's iterable but not a string, try to join text elements
            if hasattr(transcript_data, '__iter__') and not isinstance(transcript_data, str):
                try:
                    items = list(transcript_data)
                    logging.info(f"Treating as iterable with {len(items)} items")
                    
                    # Check if items have text attribute or are dictionaries with text key
                    texts = []
                    for item in items:
                        if hasattr(item, 'text'):
                            texts.append(item.text.strip())
                        elif isinstance(item, dict) and 'text' in item:
                            texts.append(item['text'].strip())
                        elif isinstance(item, str):
                            texts.append(item.strip())
                    
                    if texts:
                        return " ".join(texts)
                except Exception as e:
                    logging.warning(f"Failed to extract texts from iterable: {e}")
            
            # Last resort: try to convert to string
            try:
                result = str(transcript_data)
                logging.info(f"Converted to string with length: {len(result)}")
                return result
            except Exception as e:
                logging.error(f"Failed to convert transcript to string: {e}")
                return ""
    except Exception as e:
        logging.error(f"Error formatting transcript: {str(e)}", exc_info=True)
        return ""