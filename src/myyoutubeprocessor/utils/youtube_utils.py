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
import os

# Adding requirement for transcript extraction
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
except ImportError:
    logging.warning("youtube_transcript_api not installed. Transcript extraction won't work.")

# Import audio transcription utilities for fallback
try:
    from .audio_transcription import (
        transcribe_youtube_audio, 
        AudioTranscriptionError, 
        is_audio_transcription_available
    )
    AUDIO_TRANSCRIPTION_AVAILABLE = True
except ImportError:
    logging.warning("Audio transcription utilities not available. Audio fallback won't work.")
    AUDIO_TRANSCRIPTION_AVAILABLE = False

# Import AI enhancement utilities
try:
    from .ai.ai_service import get_ai_summary
    AI_ENHANCEMENT_AVAILABLE = True
except ImportError:
    logging.warning("AI enhancement utilities not available. AI enhancement won't work.")
    AI_ENHANCEMENT_AVAILABLE = False


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


def extract_transcript(youtube_id: str, language_code: str = 'auto', return_raw: bool = False) -> Union[Tuple[str, bool, str], Tuple[str, bool, str, Union[List, Dict, object]]]:
    """
    Extract transcript for a YouTube video using youtube_transcript_api with improved language detection.
    
    Args:
        youtube_id (str): YouTube video ID
        language_code (str): Preferred language code (default: 'auto' for automatic detection)
        return_raw (bool): Whether to return the raw transcript data along with the formatted text
        
    Returns:
        Union[Tuple[str, bool, str], Tuple[str, bool, str, object]]: 
            - If return_raw=False: (transcript_text, is_auto_generated, language_code)
            - If return_raw=True: (transcript_text, is_auto_generated, language_code, raw_data)
            
    Note:
        When language_code is 'auto', the function will automatically detect and use
        the best available transcript. For specific languages, it will try that language
        first before falling back to available alternatives.
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
        
        transcript_list = None
        available_languages = []
        manual_languages = []
        auto_languages = []
        
        # First attempt: Try to get transcript list safely with error handling
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(youtube_id)
            available_languages = [t.language_code for t in transcript_list]
            manual_languages = [t.language_code for t in transcript_list if not t.is_generated]
            auto_languages = [t.language_code for t in transcript_list if t.is_generated]
            
            logging.info(f"Available transcript languages for {youtube_id}: {available_languages}")
            logging.info(f"Manual transcripts: {manual_languages}")
            logging.info(f"Auto-generated transcripts: {auto_languages}")
        except Exception as e:
            logging.warning(f"Error getting transcript list for {youtube_id}: {str(e)}")
            # We'll try direct transcript access methods later
            
        transcript = None
        transcript_data = None
        is_generated = True
        actual_language = language_code
        
        # Enhanced language priority based on input
        priority_languages = []
        
        if transcript_list is not None:
            if language_code == 'auto':
                # Automatic detection: prioritize original language content
                
                # First priority: manual transcripts (usually in the video's original language)
                # Sort manual languages to prioritize non-English languages first (likely original content)
                manual_non_english = [lang for lang in manual_languages if not lang.startswith('en')]
                manual_english = [lang for lang in manual_languages if lang.startswith('en')]
                
                # Prioritize non-English manual transcripts first
                if manual_non_english:
                    priority_languages.extend(manual_non_english)
                    logging.info(f"Found non-English manual transcripts (prioritized): {manual_non_english}")
                
                # Then English manual transcripts
                if manual_english:
                    priority_languages.extend(manual_english)
                    logging.info(f"Found English manual transcripts: {manual_english}")
                
                # Second priority: auto-generated transcripts in non-English languages
                auto_non_english = [lang for lang in auto_languages if not lang.startswith('en')]
                auto_english = [lang for lang in auto_languages if lang.startswith('en')]
                
                if auto_non_english:
                    priority_languages.extend(auto_non_english)
                    logging.info(f"Found non-English auto-generated transcripts: {auto_non_english}")
                
                # Finally, English auto-generated as last resort
                if auto_english:
                    priority_languages.extend(auto_english)
                    logging.info(f"Found English auto-generated transcripts: {auto_english}")
                    
            else:
                # Specific language requested - comprehensive variant checking
                
                # Start with exact match
                if language_code in available_languages:
                    priority_languages.append(language_code)
                
                # Add all related language variants
                language_variants = _get_language_variants(language_code)
                for variant in language_variants:
                    if variant in available_languages and variant not in priority_languages:
                        priority_languages.append(variant)
                
                # Add manual transcripts in the requested language family
                base_lang = language_code.split('-')[0]
                for lang in manual_languages:
                    lang_base = lang.split('-')[0]
                    if lang_base == base_lang and lang not in priority_languages:
                        priority_languages.append(lang)
                
                # Add auto-generated transcripts in the requested language family
                for lang in auto_languages:
                    lang_base = lang.split('-')[0]
                    if lang_base == base_lang and lang not in priority_languages:
                        priority_languages.append(lang)
                
                # Add any remaining manual transcripts as fallback
                for lang in manual_languages:
                    if lang not in priority_languages:
                        priority_languages.append(lang)
                
                # Add any remaining auto-generated transcripts
                for lang in auto_languages:
                    if lang not in priority_languages:
                        priority_languages.append(lang)
            
            logging.info(f"Language priority order: {priority_languages}")
            
            # Try each language in priority order
            for lang in priority_languages:
                try:
                    logging.info(f"Attempting to get transcript in language: {lang}")
                    transcript = transcript_list.find_transcript([lang])
                    transcript_data = transcript.fetch()
                    is_generated = transcript.is_generated
                    actual_language = transcript.language_code
                    
                    logging.info(f"Successfully found {'manual' if not is_generated else 'auto-generated'} transcript in {actual_language}")
                    break
                    
                except NoTranscriptFound:
                    logging.info(f"No transcript found for language: {lang}")
                    continue
                except Exception as e:
                    logging.warning(f"Error fetching transcript for language {lang}: {str(e)}")
                    continue
            
            # If still no transcript found, try the first available
            if not transcript_data:
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    try:
                        first_transcript = available_transcripts[0]
                        transcript_data = first_transcript.fetch()
                        is_generated = first_transcript.is_generated
                        actual_language = first_transcript.language_code
                        logging.info(f"Using first available transcript in {actual_language}")
                    except Exception as e:
                        logging.warning(f"Failed to fetch first available transcript: {str(e)}")
                        # Reset transcript_data to None since fetch failed
                        transcript_data = None
        
        # If we still don't have transcript data, try direct API methods as fallback
        if not transcript_data:
            logging.info("Attempting direct transcript fetch as fallback")
            try:
                # Try the original direct method for auto-detection
                if language_code == 'auto':
                    transcript_data = YouTubeTranscriptApi.get_transcript(youtube_id)
                    is_generated = True  # Assume auto-generated for direct fetch
                    actual_language = 'auto'
                    logging.info("Successfully fetched transcript using direct auto method")
                else:
                    # Try specific language first, then fall back to auto
                    try:
                        transcript_data = YouTubeTranscriptApi.get_transcript(youtube_id, languages=[language_code])
                        is_generated = True  # We can't determine this easily with direct fetch
                        actual_language = language_code
                        logging.info(f"Successfully fetched transcript using direct method for {language_code}")
                    except:
                        transcript_data = YouTubeTranscriptApi.get_transcript(youtube_id)
                        is_generated = True
                        actual_language = 'auto'
                        logging.info("Successfully fetched transcript using direct auto method as fallback")
            except Exception as e:
                logging.warning(f"Direct transcript fetch also failed: {str(e)}")
                transcript_data = None
                   
        # Only proceed with formatting if we have valid transcript data
        if transcript_data:
            if isinstance(transcript_data, list) and transcript_data:
                logging.info(f"First transcript segment: {transcript_data[0]}")
                logging.info(f"Total segments: {len(transcript_data)}")
            elif hasattr(transcript_data, 'text'):
                logging.info(f"Text preview: {transcript_data.text[:50]}...")
            
            # Format the transcript into plain text
            formatted_text = _format_transcript(transcript_data)
            
            if not formatted_text:
                logging.warning(f"Failed to format transcript for video {youtube_id}")
                return ("", False, "") if not return_raw else ("", False, "", None)
                
            # Check if transcript is empty after formatting
            if not formatted_text.strip():
                logging.warning(f"Transcript for video {youtube_id} is empty after formatting")
                return ("", False, "") if not return_raw else ("", False, "", None)
            else:
                logging.info(f"Formatted transcript length: {len(formatted_text)} chars, preview: {formatted_text[:50]}...")
                
            # Log completion
            logging.info(f"Successfully extracted transcript for video {youtube_id} in {actual_language}")
            
            if return_raw:
                return formatted_text, is_generated, actual_language, transcript_data
            else:
                return formatted_text, is_generated, actual_language
        else:
            logging.warning(f"No transcript data could be extracted for video {youtube_id}")
            return ("", False, "") if not return_raw else ("", False, "", None)
    except TranscriptsDisabled as e:
        logging.warning(f"Transcripts are disabled for video {youtube_id}: {str(e)}")
        
        # Fallback to audio transcription if available
        if AUDIO_TRANSCRIPTION_AVAILABLE:
            logging.info("Attempting audio transcription as fallback for disabled transcripts")
            try:
                # Check if audio transcription is properly configured
                availability = is_audio_transcription_available()
                if not availability.get('any_available', False):
                    missing_components = [k for k, v in availability.items() if not v and k != 'any_available']
                    logging.warning(f"Audio transcription not available - missing: {', '.join(missing_components)}")
                    return ("", False, "") if not return_raw else ("", False, "", None)
                
                # Get transcription preferences from environment
                preferred_method = os.getenv('AUDIO_TRANSCRIPTION_METHOD', 'whisper')
                max_duration = int(os.getenv('MAX_AUDIO_DURATION', '1800'))  # 30 minutes default
                
                # Determine language hint for audio transcription
                language_hint = None if language_code == 'auto' else language_code.split('-')[0]
                
                transcript_text, is_auto_generated, detected_language, raw_data = transcribe_youtube_audio(
                    youtube_id=youtube_id,
                    language=language_hint,
                    preferred_method=preferred_method,
                    max_duration=max_duration,
                    cleanup=True
                )
                
                if transcript_text and len(transcript_text.strip()) > 10:
                    logging.info(f"Successfully transcribed audio for {youtube_id}: {len(transcript_text)} characters")
                    
                    # Enhance with AI if available and transcript is substantial
                    if AI_ENHANCEMENT_AVAILABLE and len(transcript_text) > 100:
                        try:
                            logging.info("Enhancing audio transcript with AI")
                            enhanced_summary = get_ai_summary(transcript_text)
                            if enhanced_summary:
                                # Add enhancement note to raw data
                                if raw_data:
                                    raw_data['ai_enhanced'] = True
                                    raw_data['ai_summary'] = enhanced_summary
                                logging.info("Successfully enhanced audio transcript with AI")
                        except Exception as e:
                            logging.warning(f"AI enhancement failed: {str(e)}")
                    
                    if return_raw:
                        return transcript_text, is_auto_generated, detected_language, raw_data
                    else:
                        return transcript_text, is_auto_generated, detected_language
                else:
                    logging.warning("Audio transcription returned insufficient content")
                    return ("", False, "") if not return_raw else ("", False, "", None)
                    
            except AudioTranscriptionError as e:
                logging.warning(f"Audio transcription failed: {str(e)}")
                return ("", False, "") if not return_raw else ("", False, "", None)
            except Exception as e:
                logging.error(f"Error during audio transcription fallback: {str(e)}", exc_info=True)
                return ("", False, "") if not return_raw else ("", False, "", None)
        else:
            logging.warning("Audio transcription not available, cannot fallback")
            return ("", False, "") if not return_raw else ("", False, "", None)
            
    except NoTranscriptFound as e:
        logging.warning(f"No transcript found for video {youtube_id}: {str(e)}")
        
        # Fallback to audio transcription if available
        if AUDIO_TRANSCRIPTION_AVAILABLE:
            logging.info("Attempting audio transcription as fallback for no transcript found")
            try:
                # Check if audio transcription is properly configured
                availability = is_audio_transcription_available()
                if not availability.get('any_available', False):
                    missing_components = [k for k, v in availability.items() if not v and k != 'any_available']
                    logging.warning(f"Audio transcription not available - missing: {', '.join(missing_components)}")
                    return ("", False, "") if not return_raw else ("", False, "", None)
                
                # Get transcription preferences from environment
                preferred_method = os.getenv('AUDIO_TRANSCRIPTION_METHOD', 'whisper')
                max_duration = int(os.getenv('MAX_AUDIO_DURATION', '1800'))  # 30 minutes default
                
                # Determine language hint for audio transcription
                language_hint = None if language_code == 'auto' else language_code.split('-')[0]
                
                transcript_text, is_auto_generated, detected_language, raw_data = transcribe_youtube_audio(
                    youtube_id=youtube_id,
                    language=language_hint,
                    preferred_method=preferred_method,
                    max_duration=max_duration,
                    cleanup=True
                )
                
                if transcript_text and len(transcript_text.strip()) > 10:
                    logging.info(f"Successfully transcribed audio for {youtube_id}: {len(transcript_text)} characters")
                    
                    # Enhance with AI if available and transcript is substantial
                    if AI_ENHANCEMENT_AVAILABLE and len(transcript_text) > 100:
                        try:
                            logging.info("Enhancing audio transcript with AI")
                            enhanced_summary = get_ai_summary(transcript_text)
                            if enhanced_summary:
                                # Add enhancement note to raw data
                                if raw_data:
                                    raw_data['ai_enhanced'] = True
                                    raw_data['ai_summary'] = enhanced_summary
                                logging.info("Successfully enhanced audio transcript with AI")
                        except Exception as e:
                            logging.warning(f"AI enhancement failed: {str(e)}")
                    
                    if return_raw:
                        return transcript_text, is_auto_generated, detected_language, raw_data
                    else:
                        return transcript_text, is_auto_generated, detected_language
                else:
                    logging.warning("Audio transcription returned insufficient content")
                    return ("", False, "") if not return_raw else ("", False, "", None)
                    
            except AudioTranscriptionError as e:
                logging.warning(f"Audio transcription failed: {str(e)}")
                return ("", False, "") if not return_raw else ("", False, "", None)
            except Exception as e:
                logging.error(f"Error during audio transcription fallback: {str(e)}", exc_info=True)
                return ("", False, "") if not return_raw else ("", False, "", None)
        else:
            logging.warning("Audio transcription not available, cannot fallback")
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
        # Handle None case explicitly
        if transcript_data is None:
            logging.warning("Transcript data is None, cannot format")
            return ""
        
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
            
            formatted_text = " ".join(item['text'].strip() for item in transcript_data if 'text' in item and item['text'])
            logging.info(f"Formatted list transcript with {len(transcript_data)} segments into text of length {len(formatted_text)}")
            return formatted_text
        
        # Handle FetchedTranscriptSnippet object (new API format)
        elif hasattr(transcript_data, 'text'):
            text = transcript_data.text.strip() if transcript_data.text else ""
            logging.info(f"Extracted text from transcript object with 'text' attribute, length: {len(text)}")
            return text
        
        # For any other format, try different approaches
        else:
            logging.warning(f"Unknown transcript data format type: {type(transcript_data)}")
            
            # Try to convert to dictionary if it's a custom object
            if hasattr(transcript_data, '__dict__'):
                data_dict = transcript_data.__dict__
                logging.info(f"Converted to dict with keys: {list(data_dict.keys())}")
                
                if 'text' in data_dict and data_dict['text']:
                    return data_dict['text'].strip()
                    
            # If it's iterable but not a string, try to join text elements
            if hasattr(transcript_data, '__iter__') and not isinstance(transcript_data, str):
                try:
                    items = list(transcript_data)
                    logging.info(f"Treating as iterable with {len(items)} items")
                    
                    # Check if items have text attribute or are dictionaries with text key
                    texts = []
                    for item in items:
                        if hasattr(item, 'text') and item.text:
                            texts.append(item.text.strip())
                        elif isinstance(item, dict) and 'text' in item and item['text']:
                            texts.append(item['text'].strip())
                        elif isinstance(item, str) and item.strip():
                            texts.append(item.strip())
                    
                    if texts:
                        return " ".join(texts)
                except Exception as e:
                    logging.warning(f"Failed to extract texts from iterable: {e}")
            
            # Last resort: try to convert to string
            try:
                result = str(transcript_data).strip()
                if result and result != "None":
                    logging.info(f"Converted to string with length: {len(result)}")
                    return result
                else:
                    logging.warning("String conversion resulted in empty or 'None' string")
                    return ""
            except Exception as e:
                logging.error(f"Failed to convert transcript to string: {e}")
                return ""
    except Exception as e:
        logging.error(f"Error formatting transcript: {str(e)}", exc_info=True)
        return ""


def _get_language_variants(language_code: str) -> List[str]:
    """
    Get common language variants for a given language code.
    
    Args:
        language_code (str): Base language code (e.g., 'am' for Amharic)
        
    Returns:
        List[str]: List of language variants to try
    """
    variants = []
    
    # Enhanced language mappings with more comprehensive coverage
    language_variants = {
        'am': ['am', 'am-ET', 'amh'],  # Amharic (Ethiopia)
        'ar': ['ar', 'ar-SA', 'ar-EG', 'ar-AE', 'ar-JO', 'ar-LB', 'ar-MA'],  # Arabic
        'zh': ['zh', 'zh-CN', 'zh-TW', 'zh-Hans', 'zh-Hant', 'zh-HK'],  # Chinese
        'en': ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU', 'en-IN'],  # English
        'es': ['es', 'es-ES', 'es-MX', 'es-AR', 'es-CO', 'es-PE'],  # Spanish
        'fr': ['fr', 'fr-FR', 'fr-CA', 'fr-BE', 'fr-CH'],  # French
        'de': ['de', 'de-DE', 'de-AT', 'de-CH'],  # German
        'hi': ['hi', 'hi-IN', 'hin'],  # Hindi
        'ja': ['ja', 'ja-JP', 'jpn'],  # Japanese
        'ko': ['ko', 'ko-KR', 'kor'],  # Korean
        'pt': ['pt', 'pt-BR', 'pt-PT', 'pt-AO'],  # Portuguese
        'ru': ['ru', 'ru-RU', 'rus'],  # Russian
        'sw': ['sw', 'sw-KE', 'sw-TZ', 'sw-UG', 'swa'],  # Swahili (Kenya, Tanzania, Uganda)
        'rw': ['rw', 'rw-RW', 'kin'],  # Kinyarwanda (Rwanda)
        'tr': ['tr', 'tr-TR', 'tur'],  # Turkish
        'ti': ['ti', 'ti-ET', 'ti-ER', 'tir'],  # Tigrinya (Ethiopia/Eritrea)
        'om': ['om', 'om-ET', 'orm'],  # Oromo (Ethiopia)
        'so': ['so', 'so-SO', 'so-ET', 'som'],  # Somali
        'ha': ['ha', 'ha-NG', 'ha-GH', 'hau'],  # Hausa
        'yo': ['yo', 'yo-NG', 'yor'],  # Yoruba
        'ig': ['ig', 'ig-NG', 'ibo'],  # Igbo
        'bn': ['bn', 'bn-BD', 'bn-IN', 'ben'],  # Bengali
        'ur': ['ur', 'ur-PK', 'ur-IN', 'urd'],  # Urdu
        'fa': ['fa', 'fa-IR', 'per'],  # Persian/Farsi
        'th': ['th', 'th-TH', 'tha'],  # Thai
        'vi': ['vi', 'vi-VN', 'vie'],  # Vietnamese
        'he': ['he', 'he-IL', 'heb'],  # Hebrew
        'ta': ['ta', 'ta-IN', 'ta-LK', 'tam'],  # Tamil
        'te': ['te', 'te-IN', 'tel'],  # Telugu
        'ml': ['ml', 'ml-IN', 'mal'],  # Malayalam
        'kn': ['kn', 'kn-IN', 'kan'],  # Kannada
        'gu': ['gu', 'gu-IN', 'guj'],  # Gujarati
        'mr': ['mr', 'mr-IN', 'mar'],  # Marathi
        'ne': ['ne', 'ne-NP', 'nep'],  # Nepali
        'si': ['si', 'si-LK', 'sin'],  # Sinhala
        'my': ['my', 'my-MM', 'mya'],  # Myanmar/Burmese
        'km': ['km', 'km-KH', 'khm'],  # Khmer
        'lo': ['lo', 'lo-LA', 'lao'],  # Lao
        'ka': ['ka', 'ka-GE', 'geo'],  # Georgian
        'hy': ['hy', 'hy-AM', 'arm'],  # Armenian
        'az': ['az', 'az-AZ', 'aze'],  # Azerbaijani
        'kk': ['kk', 'kk-KZ', 'kaz'],  # Kazakh
        'ky': ['ky', 'ky-KG', 'kir'],  # Kyrgyz
        'uz': ['uz', 'uz-UZ', 'uzb'],  # Uzbek
        'tg': ['tg', 'tg-TJ', 'tgk'],  # Tajik
        'mn': ['mn', 'mn-MN', 'mon'],  # Mongolian
    }
    
    # Extract base language if it's a variant
    base_lang = language_code.split('-')[0] if '-' in language_code else language_code
    
    # Get variants for the base language
    if base_lang in language_variants:
        variants = language_variants[base_lang]
    else:
        # For unknown languages, create reasonable variants
        variants = [language_code, base_lang]
        if '-' not in language_code:
            # Add some common country variants based on the language
            # This is a heuristic for languages we don't have specific mappings for
            if len(language_code) == 2:  # ISO 639-1 format
                # Add variants with common country codes
                common_countries = ['US', 'GB', 'CA', 'AU', 'IN', 'ZA']
                variants.extend([f"{language_code}-{country}" for country in common_countries])
    
    return variants