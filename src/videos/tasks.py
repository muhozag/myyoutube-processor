"""
Asynchronous task handlers for video processing.

This module contains functions that will be executed asynchronously using Celery.
For now, these functions are executed synchronously but are structured to be 
easily converted to Celery tasks when needed.
"""

import logging
import time
import json
import threading
import concurrent.futures
import os
from django.utils import timezone
from myyoutubeprocessor.utils.youtube_utils import extract_transcript
# Replace direct Ollama import with our AI service
from myyoutubeprocessor.utils.ai.ai_service import get_mistral_summary as get_ai_summary

from .models import Video, Transcript

logger = logging.getLogger(__name__)

# Maximum allowed processing time in seconds (5 minutes)
MAX_PROCESSING_TIME = 300

# Import audio transcription utilities
try:
    from myyoutubeprocessor.utils.audio_transcription import (
        transcribe_youtube_audio, 
        is_audio_transcription_available,
        AudioTranscriptionError
    )
    AUDIO_TRANSCRIPTION_AVAILABLE = True
except ImportError:
    logger.warning("Audio transcription utilities not available")
    AUDIO_TRANSCRIPTION_AVAILABLE = False

def try_audio_transcription(video_id, youtube_id, language_hint=None):
    """
    Attempt to transcribe video audio when no YouTube transcript is available.
    
    Args:
        video_id (int): Database video ID
        youtube_id (str): YouTube video ID
        language_hint (str): Optional language hint for transcription
        
    Returns:
        tuple: (success, transcript_data, error_msg)
    """
    if not AUDIO_TRANSCRIPTION_AVAILABLE:
        return False, None, "Audio transcription not available - missing dependencies"
    
    # Check if audio transcription is properly configured
    availability = is_audio_transcription_available()
    if not availability.get('any_available', False):
        missing_components = [k for k, v in availability.items() if not v and k != 'any_available']
        return False, None, f"Audio transcription not available - missing: {', '.join(missing_components)}"
    
    try:
        logger.info(f"Attempting audio transcription for video {youtube_id}")
        
        # Get transcription preferences from environment
        preferred_method = os.getenv('AUDIO_TRANSCRIPTION_METHOD', 'whisper')
        max_duration = int(os.getenv('MAX_AUDIO_DURATION', '1800'))  # 30 minutes default
        
        # Try to transcribe the audio
        transcript_text, is_auto_generated, detected_language, raw_data = transcribe_youtube_audio(
            youtube_id=youtube_id,
            language=language_hint,
            preferred_method=preferred_method,
            max_duration=max_duration,
            cleanup=True
        )
        
        if transcript_text and len(transcript_text.strip()) > 10:  # Minimum length check
            logger.info(f"Successfully transcribed audio for {youtube_id}: {len(transcript_text)} characters")
            return True, (transcript_text, is_auto_generated, detected_language, raw_data), None
        else:
            return False, None, "Audio transcription returned insufficient content"
            
    except AudioTranscriptionError as e:
        error_msg = f"Audio transcription failed: {str(e)}"
        logger.warning(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during audio transcription: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, None, error_msg


def handle_video_without_transcript(video, error_msg):
    """
    Handle videos that don't have available transcripts by trying audio transcription,
    then setting appropriate status if that also fails.
    
    Args:
        video: Video model instance
        error_msg (str): The error message describing why no transcript was found
    """
    # First, try audio transcription as a fallback
    if AUDIO_TRANSCRIPTION_AVAILABLE:
        logger.info(f"Attempting audio transcription fallback for video {video.youtube_id}")
        
        try:
            success, transcript_result, audio_error = try_audio_transcription(
                video.id, 
                video.youtube_id,
                language_hint=None  # Let it auto-detect
            )
            
            if success and transcript_result:
                transcript_text, is_auto_generated, language_code, raw_data = transcript_result
                
                # Save the audio-transcribed content
                transcript, created = Transcript.objects.update_or_create(
                    video=video,
                    defaults={
                        'content': transcript_text,
                        'language': language_code,
                        'is_auto_generated': True,  # Mark as auto-generated since it's from audio
                        'raw_transcript_data': raw_data
                    }
                )
                
                # Generate beautified content
                transcript.beautify_transcript(raw_data)
                
                # Try to generate summary
                try:
                    from myyoutubeprocessor.utils.ai.ai_service import get_mistral_summary as get_ai_summary
                    summary = get_ai_summary(transcript_text)
                    if summary:
                        transcript.summary = summary
                        transcript.save(update_fields=['summary', 'updated_at'])
                        logger.info(f'Generated summary for audio-transcribed video {video.youtube_id}')
                except Exception as e:
                    logger.warning(f'Summary generation failed for audio-transcribed video: {e}')
                
                # Mark video as completed
                video.processing_status = 'completed'
                video.processing_completed_at = timezone.now()
                video.error_message = f"Completed via audio transcription (original issue: {error_msg})"
                video.save()
                
                logger.info(f"Successfully processed video {video.youtube_id} via audio transcription")
                return True
                
            else:
                logger.info(f"Audio transcription also failed for {video.youtube_id}: {audio_error}")
                # Continue to the original handling below
                
        except Exception as e:
            logger.error(f"Error during audio transcription fallback for {video.youtube_id}: {str(e)}")
            # Continue to the original handling below
    
    # Original handling when audio transcription is not available or also failed
    if any(phrase in error_msg.lower() for phrase in [
        'no transcript', 'transcript not available', 'transcripts disabled',
        'empty content', 'content too short', 'audio transcription failed'
    ]):
        # This is a transcript availability issue, not a technical failure
        logger.info(f"Video {video.youtube_id} has no available transcript: {error_msg}")
        
        # Create a minimal transcript record to indicate we tried
        transcript, created = Transcript.objects.update_or_create(
            video=video,
            defaults={
                'content': '',
                'language': 'unavailable',
                'is_auto_generated': False,
                'summary': f'No transcript available for this video. Reason: {error_msg}',
                'raw_transcript_data': None
            }
        )
        
        # Mark video as completed but note the transcript limitation
        video.processing_status = 'completed'
        video.processing_completed_at = timezone.now()
        video.error_message = f"Completed with limitation: {error_msg}"
        video.save()
        
        return True
    else:
        # This is a technical error
        video.mark_failed(error_msg)
        return False


def try_transcript_with_multiple_strategies(video_id, youtube_id):
    """
    Try multiple strategies to extract transcript for videos that initially failed.
    Now includes audio transcription as a final fallback with improved language detection
    and uses the video's preferred language setting.
    
    Args:
        video_id (int): Database video ID
        youtube_id (str): YouTube video ID
        
    Returns:
        tuple: (success, transcript_data, error_msg)
    """
    # Get the video instance to access the preferred language
    try:
        from .models import Video
        video = Video.objects.get(pk=video_id)
        preferred_language = video.preferred_language
        logger.info(f"Video {youtube_id} has preferred language: {preferred_language}")
    except Video.DoesNotExist:
        logger.warning(f"Video with ID {video_id} not found, using auto-detection")
        preferred_language = 'auto'
    except Exception as e:
        logger.warning(f"Error getting video preferred language: {str(e)}, using auto-detection")
        preferred_language = 'auto'
    
    strategies = []
    
    # If user selected a specific language, prioritize it
    if preferred_language != 'auto':
        logger.info(f"Prioritizing user's preferred language: {preferred_language}")
        strategies.append({'language_code': preferred_language, 'description': f'user-selected {preferred_language}'})
        
        # Add language variants for the selected language
        from myyoutubeprocessor.utils.youtube_utils import _get_language_variants
        variants = _get_language_variants(preferred_language)
        for variant in variants:
            if variant != preferred_language:  # Don't duplicate the main language
                strategies.append({'language_code': variant, 'description': f'variant of {preferred_language} ({variant})'})
    
    # Add auto-detection as secondary strategy
    strategies.append({'language_code': 'auto', 'description': 'auto-detection with foreign language priority'})
    
    # Only add fallback languages if user chose auto-detect or if preferred language fails
    fallback_languages = [
        {'language_code': 'am', 'description': 'Amharic'},
        {'language_code': 'sw', 'description': 'Swahili'},
        {'language_code': 'rw', 'description': 'Kinyarwanda'},
        {'language_code': 'ar', 'description': 'Arabic'},
        {'language_code': 'zh', 'description': 'Chinese'},
        {'language_code': 'hi', 'description': 'Hindi'},
        {'language_code': 'ja', 'description': 'Japanese'},
        {'language_code': 'ko', 'description': 'Korean'},
        {'language_code': 'es', 'description': 'Spanish'},
        {'language_code': 'fr', 'description': 'French'},
        {'language_code': 'de', 'description': 'German'},
        {'language_code': 'pt', 'description': 'Portuguese'},
        {'language_code': 'ru', 'description': 'Russian'},
        {'language_code': 'it', 'description': 'Italian'},
        {'language_code': 'tr', 'description': 'Turkish'},
        {'language_code': 'fa', 'description': 'Persian/Farsi'},
        {'language_code': 'ur', 'description': 'Urdu'},
        {'language_code': 'bn', 'description': 'Bengali'},
        {'language_code': 'ta', 'description': 'Tamil'},
        {'language_code': 'te', 'description': 'Telugu'},
        {'language_code': 'th', 'description': 'Thai'},
        {'language_code': 'vi', 'description': 'Vietnamese'},
        {'language_code': 'he', 'description': 'Hebrew'},
        {'language_code': 'en', 'description': 'English'},
        {'language_code': 'en-US', 'description': 'English (US)'},
        {'language_code': 'en-GB', 'description': 'English (UK)'},
    ]
    
    # Add fallback languages, but skip the ones already tried
    tried_languages = {strategy['language_code'] for strategy in strategies}
    for fallback in fallback_languages:
        if fallback['language_code'] not in tried_languages:
            strategies.append(fallback)
    
    detected_language = None
    available_languages = []
    
    # First, try to get available languages to inform our strategy
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.list_transcripts(youtube_id)
        available_languages = [t.language_code for t in transcript_list]
        manual_languages = [t.language_code for t in transcript_list if not t.is_generated]
        
        logger.info(f"Available languages for {youtube_id}: {available_languages}")
        logger.info(f"Manual transcripts available: {manual_languages}")
        
        # If user selected a specific language, check if it's available
        if preferred_language != 'auto':
            if preferred_language in available_languages:
                logger.info(f"User's preferred language {preferred_language} is available")
            else:
                # Check if any variant is available
                from myyoutubeprocessor.utils.youtube_utils import _get_language_variants
                variants = _get_language_variants(preferred_language)
                available_variants = [v for v in variants if v in available_languages]
                if available_variants:
                    logger.info(f"Variants of preferred language available: {available_variants}")
                else:
                    logger.warning(f"Preferred language {preferred_language} and its variants not available. Available: {available_languages}")
        
        # If we have manual transcripts, prioritize non-English ones for auto-detection
        if preferred_language == 'auto' and manual_languages:
            non_english_manual = [lang for lang in manual_languages if not lang.startswith('en')]
            if non_english_manual:
                detected_language = non_english_manual[0]  # Use first non-English manual transcript
                logger.info(f"Detected likely original language from manual transcripts: {detected_language}")
                # Insert detected language after auto-detection
                strategies.insert(2, {'language_code': detected_language, 'description': f'detected original language ({detected_language})'})
        
    except Exception as e:
        logger.info(f"Could not pre-analyze available languages for {youtube_id}: {str(e)}")
    
    # Filter strategies to only try languages that are actually available
    if available_languages:
        filtered_strategies = []
        for strategy in strategies:
            lang_code = strategy['language_code']
            if lang_code == 'auto' or lang_code in available_languages:
                filtered_strategies.append(strategy)
            else:
                # Check if any variant of this language is available
                from myyoutubeprocessor.utils.youtube_utils import _get_language_variants
                variants = _get_language_variants(lang_code)
                if any(variant in available_languages for variant in variants):
                    filtered_strategies.append(strategy)
        
        if filtered_strategies:
            strategies = filtered_strategies
            logger.info(f"Filtered strategies to {len(strategies)} based on available languages")
        else:
            logger.warning(f"No strategies match available languages {available_languages}, trying all strategies anyway")
    
    # Try each strategy in order
    for i, strategy in enumerate(strategies):
        try:
            logger.info(f"Trying transcript extraction for {youtube_id} with {strategy['description']} (strategy {i+1}/{len(strategies)})")
            transcript_result = extract_transcript(youtube_id, strategy['language_code'], return_raw=True)
            
            if transcript_result and len(transcript_result) >= 4:
                transcript_text, is_auto_generated, language_code, raw_data = transcript_result
                
                # More lenient validation - accept even short transcripts
                if transcript_text and len(transcript_text.strip()) > 0:
                    logger.info(f"Successfully extracted transcript using {strategy['description']} strategy")
                    logger.info(f"Transcript language: {language_code}, auto-generated: {is_auto_generated}, length: {len(transcript_text)} chars")
                    return True, transcript_result, None
                    
        except Exception as e:
            logger.info(f"Strategy {strategy['description']} failed: {str(e)}")
            continue
    
    # If all YouTube transcript strategies failed, try audio transcription with language hints
    if AUDIO_TRANSCRIPTION_AVAILABLE:
        logger.info(f"All YouTube transcript strategies failed for {youtube_id}, trying audio transcription")
        
        # Use preferred language or detected language as hint for audio transcription
        language_hint = None
        if preferred_language != 'auto':
            language_hint = preferred_language
        elif detected_language:
            language_hint = detected_language
        elif available_languages:
            # Prefer non-English languages as they're more likely to be the original
            non_english_langs = [lang for lang in available_languages if not lang.startswith('en')]
            if non_english_langs:
                language_hint = non_english_langs[0].split('-')[0]  # Use base language code
        
        if language_hint:
            logger.info(f"Using language hint for audio transcription: {language_hint}")
        
        success, audio_result, audio_error = try_audio_transcription(video_id, youtube_id, language_hint)
        if success and audio_result:
            logger.info(f"Audio transcription succeeded for {youtube_id}")
            return True, audio_result, None
        else:
            logger.info(f"Audio transcription also failed for {youtube_id}: {audio_error}")
    
    # If all strategies failed, check if video exists and might have transcripts disabled
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
        
        # Try to get transcript list to see what's available
        try:
            if not available_languages:  # Only do this if we haven't already checked
                transcript_list = YouTubeTranscriptApi.list_transcripts(youtube_id)
                available_languages = [t.language_code for t in transcript_list]
            
            logger.info(f"Final check - Available transcript languages for {youtube_id}: {available_languages}")
            
            if not available_languages:
                return False, None, "No transcripts available in any language for this video"
            else:
                return False, None, f"Transcripts available in {available_languages} but extraction failed with all strategies"
                
        except TranscriptsDisabled:
            return False, None, "Transcripts are disabled for this video"
        except NoTranscriptFound:
            return False, None, "No transcripts found for this video"
        except Exception as e:
            return False, None, f"Unable to check transcript availability: {str(e)}"
            
    except ImportError:
        return False, None, "YouTube transcript API not available"

def process_video_with_timeout(video_id):
    """
    Process a video by retrieving metadata and transcript with a timeout.
    
    Args:
        video_id (int): The database ID of the video to process
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger.info(f"Starting to process video {video_id}")
    
    try:
        # Get the video from database
        video = Video.objects.get(pk=video_id)
        
        # Mark as processing
        video.mark_processing()
        logger.info(f"Processing video: {video.youtube_id}")
        
        # Try multiple transcript extraction strategies
        success, transcript_result, error_msg = try_transcript_with_multiple_strategies(video_id, video.youtube_id)
        
        if success and transcript_result:
            transcript_text, is_auto_generated, language_code, raw_data = transcript_result
            
            # Log transcript details
            logger.info(f"Got transcript for {video.youtube_id}: {len(transcript_text)} chars, language: {language_code}")
            
            # More lenient validation for non-English content
            if not transcript_text or len(transcript_text.strip()) == 0:
                error_msg = f"Transcript extraction returned empty content for {video.youtube_id}"
                logger.warning(error_msg)
                return handle_video_without_transcript(video, error_msg)
            
            # Less strict validation for short content - some videos genuinely have short transcripts
            if len(transcript_text.strip()) < 5:
                error_msg = f"Transcript content very short ({len(transcript_text)} chars) for {video.youtube_id}"
                logger.warning(error_msg)
                return handle_video_without_transcript(video, error_msg)
            
            # Convert raw_data to a serializable format if necessary
            serializable_data = None
            if raw_data is not None:
                if isinstance(raw_data, list):
                    # If it's already a list, it should be serializable
                    serializable_data = raw_data
                elif hasattr(raw_data, '__dict__'):
                    # If it's an object with attributes, try to convert to dict
                    try:
                        # Convert object to dictionary of its attributes
                        serializable_data = []
                        for item in raw_data:
                            if hasattr(item, '__dict__'):
                                item_dict = item.__dict__.copy()
                                # Remove any non-serializable items
                                for key, value in list(item_dict.items()):
                                    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                                        item_dict[key] = str(value)
                                serializable_data.append(item_dict)
                            else:
                                serializable_data.append({"text": str(item)})
                    except Exception as e:
                        logger.warning(f"Could not convert transcript data to serializable format: {str(e)}")
                        serializable_data = None
                else:
                    # If we can't figure out how to convert it, just store as string
                    try:
                        serializable_data = str(raw_data)
                    except Exception as e:
                        logger.warning(f"Failed to convert raw_data to string: {str(e)}")
                        serializable_data = None
            
            # Save transcript to database
            logger.info(f"Saving transcript for {video.youtube_id}")
            transcript, created = Transcript.objects.update_or_create(
                video=video,
                defaults={
                    'content': transcript_text,
                    'language': language_code,
                    'is_auto_generated': is_auto_generated,
                    'raw_transcript_data': serializable_data
                }
            )
            
            # Generate beautified content
            logger.info(f"Beautifying transcript for {video.youtube_id}")
            transcript.beautify_transcript(raw_data)
            
            # Generate summary using our AI service (which will use either Ollama or Mistral API)
            try:
                logger.info(f"Generating summary for transcript of {video.youtube_id}")
                
                # Add more detailed AI service logging
                from myyoutubeprocessor.utils.ai.ollama_utils import (
                    OLLAMA_HOST, OLLAMA_API_KEY, is_ollama_available, 
                    is_railway_environment, LOCAL_MODEL
                )
                
                # Check if Ollama is available
                ollama_available = is_ollama_available()
                logger.info(f"Ollama available: {ollama_available}, Host: {OLLAMA_HOST}, Railway env: {is_railway_environment()}")
                
                # Check if Mistral API is configured
                mistral_api_key = os.environ.get('MISTRAL_API_KEY')
                logger.info(f"Mistral API configured: {'Yes' if mistral_api_key else 'No'}")
                
                # Try to generate summary with proper error catching
                summary = None
                try:
                    summary = get_ai_summary(transcript_text)
                except Exception as e:
                    logger.error(f"Error in get_ai_summary: {str(e)}")
                
                if summary:
                    transcript.summary = summary
                    transcript.save(update_fields=['summary', 'updated_at'])
                    logger.info(f"Summary generated for {video.youtube_id}")
                else:
                    logger.warning(f"Failed to generate summary for {video.youtube_id} - summary is None")
            except Exception as e:
                logger.error(f"Error generating summary for {video.youtube_id}: {str(e)}")
                # Continue processing even if summary generation fails

            logger.info(f"Saved transcript for {video.youtube_id} ({language_code}, auto-generated: {is_auto_generated})")
            
            # Successfully processed
            video.mark_completed()
            logger.info(f"Successfully processed video {video.youtube_id}")
            return True
        else:
            error_msg = f"No transcript available for {video.youtube_id}"
            logger.warning(error_msg)
            video.mark_failed(error_msg)
            return False
    except Exception as transcript_error:
        error_msg = f"Error extracting transcript: {str(transcript_error)}"
        logger.exception(error_msg)
        video.mark_failed(error_msg)
        return False
            
    except Video.DoesNotExist:
        logger.error(f"Video with ID {video_id} not found")
        return False
        
    except Exception as e:
        logger.exception(f"Error processing video {video_id}: {str(e)}")
        try:
            video = Video.objects.get(pk=video_id)
            video.mark_failed(str(e))
        except Exception:
            pass
        return False

def process_video(video_id):
    """
    Process a video by retrieving metadata and transcript with a timeout of 5 minutes.
    
    Args:
        video_id (int): The database ID of the video to process
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        # Use ThreadPoolExecutor to run the processing with a timeout
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(process_video_with_timeout, video_id)
            try:
                # Wait for the result with a timeout
                return future.result(timeout=MAX_PROCESSING_TIME)
            except concurrent.futures.TimeoutError:
                # Processing took too long
                logger.error(f"Processing timed out after {MAX_PROCESSING_TIME} seconds for video {video_id}")
                try:
                    video = Video.objects.get(pk=video_id)
                    video.mark_failed(f"Processing timed out after {MAX_PROCESSING_TIME} seconds")
                except Exception as e:
                    logger.exception(f"Error marking video {video_id} as failed: {str(e)}")
                return False
    except Exception as e:
        logger.exception(f"Error in process_video wrapper for video {video_id}: {str(e)}")
        try:
            video = Video.objects.get(pk=video_id)
            video.mark_failed(str(e))
        except Exception:
            pass
        return False

# This will be converted to a Celery task
def process_video_async(video_id):
    """
    Asynchronous wrapper for processing a video. Currently runs synchronously,
    but will be converted to a Celery task in the future.
    
    Args:
        video_id (int): The database ID of the video to process
    """
    return process_video(video_id)

def generate_summary(transcript_id):
    """
    Generate a summary for an existing transcript using our AI service.
    
    Args:
        transcript_id (int): The database ID of the transcript
        
    Returns:
        bool: True if summary generation was successful, False otherwise
    """
    try:
        transcript = Transcript.objects.get(pk=transcript_id)
        logger.info(f"Generating summary for transcript {transcript_id}")
        
        # Log detailed environment information to help debug AI connection issues
        from myyoutubeprocessor.utils.ai.ollama_utils import (
            OLLAMA_HOST, OLLAMA_API_KEY, is_ollama_available, 
            is_railway_environment, LOCAL_MODEL
        )
        
        # Check if Ollama is available
        ollama_available = is_ollama_available()
        logger.info(f"Ollama available: {ollama_available}, Host: {OLLAMA_HOST}, Has API Key: {'Yes' if OLLAMA_API_KEY else 'No'}")
        
        # Check if Mistral API is configured
        mistral_api_key = os.environ.get('MISTRAL_API_KEY')
        logger.info(f"Mistral API configured: {'Yes' if mistral_api_key else 'No'}")
        
        # Log environment information
        logger.info(f"Railway environment: {is_railway_environment()}, Production mode: {bool(os.environ.get('RAILWAY_SERVICE_NAME') or not os.environ.get('DEBUG', '').lower() == 'true')}")
        
        # Attempt to generate summary with additional error details
        summary = get_ai_summary(transcript.content)
        
        if summary:
            transcript.summary = summary
            transcript.save(update_fields=['summary', 'updated_at'])
            logger.info(f"Summary generated for transcript {transcript_id}")
            return True
        else:
            logger.warning(f"Failed to generate summary for transcript {transcript_id} - AI service returned None")
            return False
    except Transcript.DoesNotExist:
        logger.error(f"Transcript with ID {transcript_id} not found")
        return False
    except ImportError as e:
        logger.error(f"Import error while generating summary: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Error generating summary for transcript {transcript_id}: {str(e)}")
        return False