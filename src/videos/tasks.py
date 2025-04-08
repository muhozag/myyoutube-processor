"""
Asynchronous task handlers for video processing.

This module contains functions that will be executed asynchronously using Celery.
For now, these functions are executed synchronously but are structured to be 
easily converted to Celery tasks when needed.
"""

import logging
import time
import json
from django.utils import timezone
from myyoutubeprocessor.utils.youtube_utils import extract_transcript

from .models import Video, Transcript

logger = logging.getLogger(__name__)

def process_video(video_id):
    """
    Process a video by retrieving metadata and transcript.
    
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
        
        # Fetch and update video metadata
        # In a real implementation, this would call the YouTube API
        # For now, we'll simulate a successful metadata update
        
        # Simulate processing delay
        time.sleep(2)
        
        # Extract transcript using our utility function
        transcript_result = extract_transcript(video.youtube_id, return_raw=True)
        
        if transcript_result:
            transcript_text, is_auto_generated, language_code, raw_data = transcript_result
            
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
                    except Exception:
                        serializable_data = None
            
            # Save transcript to database
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
            transcript.beautify_transcript(raw_data)
            
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

# This will be converted to a Celery task
def process_video_async(video_id):
    """
    Asynchronous wrapper for processing a video. Currently runs synchronously,
    but will be converted to a Celery task in the future.
    
    Args:
        video_id (int): The database ID of the video to process
    """
    return process_video(video_id)