from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
import logging
import threading
import os

from .models import Video, Transcript
from .forms import VideoSubmissionForm
from .tasks import process_video_async, generate_summary, process_video as process_video_task
from myyoutubeprocessor.utils.ai.ollama_utils import format_metadata

# Set up logger
logger = logging.getLogger(__name__)

# Check if we're running on Railway or other production environment
IS_PRODUCTION = bool(os.environ.get('RAILWAY_SERVICE_NAME') or not os.environ.get('DEBUG', '').lower() == 'true')

class VideoListView(ListView):
    """Display list of videos with their processing status"""
    model = Video
    template_name = 'videos/video_list.html'
    context_object_name = 'videos'
    paginate_by = 10
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        return context

class VideoDetailView(DetailView):
    """Display detailed information about a video"""
    model = Video
    template_name = 'videos/video_detail.html'
    context_object_name = 'video'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = self.object
        
        # Generate formatted metadata using our utility function
        # Using created_at (when video was added to our app) for processed_time
        processed_time = video.created_at.isoformat() if video.created_at else None
        context['formatted_metadata'] = format_metadata(
            youtube_id=video.youtube_id,
            processed_time=processed_time,
            processing_time=video.processing_time
        )
        
        return context

class VideoCreateView(CreateView):
    """Form to submit new YouTube videos for processing"""
    model = Video
    form_class = VideoSubmissionForm
    template_name = 'videos/video_submit.html'
    success_url = reverse_lazy('video_list')
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, f"Video '{self.object.title or self.object.youtube_id}' has been submitted for processing.")
            
            # In production environments, we'll process synchronously to avoid thread issues
            if IS_PRODUCTION:
                try:
                    process_video_task(self.object.pk)
                except Exception as e:
                    logger.exception(f"Error processing video synchronously: {str(e)}")
            else:
                # Only use threading in development
                thread = threading.Thread(
                    target=process_video_async,
                    args=(self.object.pk,),
                    daemon=True
                )
                thread.start()
            
            return response
        except ValidationError as e:
            form.add_error('url', e)
            return self.form_invalid(form)
        except Exception as e:
            logger.exception(f"Error processing video: {str(e)}")
            form.add_error(None, f"An unexpected error occurred: {str(e)}")
            return self.form_invalid(form)

@require_POST
def process_video(request, pk):
    """Trigger processing for a specific video"""
    video = get_object_or_404(Video, pk=pk)
    
    try:
        # Mark as processing first so the UI shows the right status
        video.mark_processing()
        
        # In production environments, we'll process synchronously to avoid thread issues
        if IS_PRODUCTION:
            try:
                process_video_task(video.pk)
            except Exception as e:
                logger.exception(f"Error processing video synchronously: {str(e)}")
                video.mark_failed(str(e))
        else:
            # Only use threading in development
            thread = threading.Thread(
                target=process_video_async,
                args=(video.pk,),
                daemon=True
            )
            thread.start()
        
        messages.success(request, f"Video '{video.title or video.youtube_id}' is being processed.")
    except Exception as e:
        logger.exception(f"Error processing video {video.pk}: {str(e)}")
        video.mark_failed(str(e))
        messages.error(request, f"Error processing video: {str(e)}")
    
    return redirect('video_detail', pk=video.pk)

@require_POST
def process_video_by_id(request, video_id):
    """Alternative entry point for processing a video, using video_id instead of pk"""
    # This is just a wrapper around the main process_video function
    logger.info(f"process_video_by_id called with video_id={video_id}")
    return process_video(request, video_id)

def video_status(request, pk):
    """API endpoint to check video processing status"""
    try:
        video = get_object_or_404(Video, pk=pk)
        return JsonResponse({
            'id': video.pk,
            'youtube_id': video.youtube_id,
            'status': video.status,
            'is_processed': video.is_processed,
            'processing_time': video.processing_time,
            'error': video.error_message if video.status == 'failed' else None
        })
    except Exception as e:
        logger.exception(f"Error getting video status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
def generate_transcript_summary(request, pk):
    """Generate or regenerate a summary for an existing transcript"""
    video = get_object_or_404(Video, pk=pk)
    
    try:
        # Verify transcript exists
        if not hasattr(video, 'transcript'):
            messages.error(request, "Cannot generate summary: No transcript found for this video.")
            return redirect('video_detail', pk=video.pk)
        
        # First, check if Ollama is available by importing and using the function
        from myyoutubeprocessor.utils.ai.ollama_utils import is_ollama_available
        ollama_available = is_ollama_available()
        
        # Check for Mistral API key if we might need to use that service
        mistral_api_key = os.environ.get('MISTRAL_API_KEY')
        
        # If no AI services are available, show a clear error message
        if not ollama_available and not mistral_api_key:
            messages.error(request, "Cannot generate summary: No AI services are available. Please ensure Ollama is running or Mistral API key is configured.")
            logger.error("Summary generation failed: No AI services available")
            return redirect('video_detail', pk=video.pk)
        
        # In production environments, we'll process synchronously to avoid thread issues
        if IS_PRODUCTION:
            try:
                summary_result = generate_summary(video.transcript.pk)
                if not summary_result:
                    messages.error(request, "Failed to generate summary. Check application logs for details.")
                    return redirect('video_detail', pk=video.pk)
            except Exception as e:
                logger.exception(f"Error generating summary synchronously: {str(e)}")
                messages.error(request, f"Error generating summary: {str(e)}")
                return redirect('video_detail', pk=video.pk)
        else:
            # Only use threading in development
            thread = threading.Thread(
                target=generate_summary,
                args=(video.transcript.pk,),
                daemon=True
            )
            thread.start()
        
        messages.success(request, f"Generating summary for '{video.title or video.youtube_id}'. Please refresh in a few moments.")
    except Exception as e:
        logger.exception(f"Error generating summary for video {video.pk}: {str(e)}")
        messages.error(request, f"Error generating summary: {str(e)}")
    
    return redirect('video_detail', pk=video.pk)

@require_POST
def delete_video(request, pk):
    """Delete a video and its associated data"""
    video = get_object_or_404(Video, pk=pk)
    video_title = video.title or video.youtube_id
    
    try:
        video.delete()
        messages.success(request, f"Video '{video_title}' has been deleted.")
        logger.info(f"Video {pk} ({video_title}) was deleted")
    except Exception as e:
        logger.exception(f"Error deleting video {pk}: {str(e)}")
        messages.error(request, f"Error deleting video: {str(e)}")
    
    return redirect('video_list')
