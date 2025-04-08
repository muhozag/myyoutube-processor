"""
Asynchronous task handlers for video processing.

This module contains functions that will be executed asynchronously using Celery.
For now, these functions are executed synchronously but are structured to be 
easily converted to Celery tasks when needed.
"""

import logging
import time
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
        transcript_text, is_auto_generated, language_code = extract_transcript(video.youtube_id)
        
        if transcript_text:
            # Save transcript to database
            transcript, created = Transcript.objects.update_or_create(
                video=video,
                defaults={
                    'content': transcript_text,
                    'language': language_code,
                    'is_auto_generated': is_auto_generated
                }
            )
            
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