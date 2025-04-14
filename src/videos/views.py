from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError, PermissionDenied
import logging
import threading
import os

from .models import Video, Transcript
from .forms import VideoSubmissionForm
from .tasks import process_video_async, generate_summary, process_video as process_video_task
from myyoutubeprocessor.utils.ai.ollama_utils import format_metadata, get_current_model_info

# Set up logger
logger = logging.getLogger(__name__)

# Check if we're running on Railway or other production environment
IS_PRODUCTION = bool(os.environ.get('RAILWAY_SERVICE_NAME') or not os.environ.get('DEBUG', '').lower() == 'true')

@method_decorator(login_required, name='dispatch')
class VideoListView(LoginRequiredMixin, ListView):
    """Display list of videos with their processing status"""
    model = Video
    template_name = 'videos/video_list.html'
    context_object_name = 'videos'
    paginate_by = 10
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # If not staff/admin, only show videos for the current user
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
            
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        return context

@method_decorator(login_required, name='dispatch')
class VideoDetailView(LoginRequiredMixin, DetailView):
    """Display detailed information about a video"""
    model = Video
    template_name = 'videos/video_detail.html'
    context_object_name = 'video'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Check if the user has permission to view this video
        if not self.request.user.is_staff and obj.user and obj.user != self.request.user:
            raise PermissionDenied("You don't have permission to view this video")
        return obj
    
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
        
        # Add AI model information to the context
        context['ai_model_info'] = get_current_model_info()
        
        return context

@method_decorator(login_required, name='dispatch')
class VideoCreateView(LoginRequiredMixin, CreateView):
    """Form to submit new YouTube videos for processing"""
    model = Video
    form_class = VideoSubmissionForm
    template_name = 'videos/video_submit.html'
    success_url = reverse_lazy('video_list')
    
    def form_valid(self, form):
        try:
            # Set the current user as the owner of the video
            form.instance.user = self.request.user
            
            response = super().form_valid(form)
            messages.success(self.request, f"Video '{self.object.title or self.object.youtube_id}' has been submitted for processing.")
            
            # Don't process immediately - only mark as pending and redirect
            # This prevents timeouts during the submission process
            logger.info(f"Video '{self.object.youtube_id}' submitted. Processing will start separately.")
            
            # Create a background thread to process the video after the response is sent
            # This is a workaround until we implement a proper task queue
            def delayed_processing():
                try:
                    # Wait a few seconds to ensure the response has been sent
                    import time
                    time.sleep(2)
                    
                    # Start processing
                    logger.info(f"Starting delayed processing for video {self.object.pk}")
                    process_video_task(self.object.pk)
                except Exception as e:
                    logger.exception(f"Error in delayed processing of video {self.object.pk}: {str(e)}")
            
            # Start delayed processing thread
            processing_thread = threading.Thread(
                target=delayed_processing,
                daemon=True
            )
            processing_thread.start()
            
            return response
        except ValidationError as e:
            form.add_error('url', e)
            return self.form_invalid(form)
        except Exception as e:
            logger.exception(f"Error processing video: {str(e)}")
            form.add_error(None, f"An unexpected error occurred: {str(e)}")
            return self.form_invalid(form)

@login_required
@require_POST
def process_video(request, pk):
    """Trigger processing for a specific video"""
    video = get_object_or_404(Video, pk=pk)
    
    # Check permission
    if not request.user.is_staff and video.user and video.user != request.user:
        raise PermissionDenied("You don't have permission to process this video")
    
    try:
        # Mark as processing first so the UI shows the right status
        video.mark_processing()
        
        # Always use asynchronous processing to prevent request timeouts
        def delayed_processing():
            try:
                # Wait a few seconds to ensure the response has been sent
                import time
                time.sleep(2)
                
                # Start processing
                logger.info(f"Starting delayed processing for video {video.pk}")
                process_video_task(video.pk)
            except Exception as e:
                logger.exception(f"Error in delayed processing of video {video.pk}: {str(e)}")
                try:
                    video.mark_failed(str(e))
                except Exception:
                    pass
        
        # Start delayed processing thread
        processing_thread = threading.Thread(
            target=delayed_processing,
            daemon=True
        )
        processing_thread.start()
        
        messages.success(request, f"Video '{video.title or video.youtube_id}' is being processed.")
    except Exception as e:
        logger.exception(f"Error processing video {video.pk}: {str(e)}")
        video.mark_failed(str(e))
        messages.error(request, f"Error processing video: {str(e)}")
    
    return redirect('video_detail', pk=video.pk)

@login_required
@require_POST
def process_video_by_id(request, video_id):
    """Alternative entry point for processing a video, using video_id instead of pk"""
    # This is just a wrapper around the main process_video function
    logger.info(f"process_video_by_id called with video_id={video_id}")
    return process_video(request, video_id)

@login_required
def video_status(request, pk):
    """API endpoint to check video processing status"""
    try:
        video = get_object_or_404(Video, pk=pk)
        
        # Check permission
        if not request.user.is_staff and video.user and video.user != request.user:
            raise PermissionDenied("You don't have permission to view this video's status")
            
        return JsonResponse({
            'id': video.pk,
            'youtube_id': video.youtube_id,
            'status': video.status,
            'is_processed': video.is_processed,
            'processing_time': video.processing_time,
            'error': video.error_message if video.status == 'failed' else None
        })
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
    except Exception as e:
        logger.exception(f"Error getting video status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def generate_transcript_summary(request, pk):
    """Generate or regenerate a summary for an existing transcript"""
    video = get_object_or_404(Video, pk=pk)
    
    # Check permission
    if not request.user.is_staff and video.user and video.user != request.user:
        raise PermissionDenied("You don't have permission to generate a summary for this video")
    
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
        
        # Always use asynchronous processing to prevent request timeouts
        def delayed_summary_generation():
            try:
                # Wait a few seconds to ensure the response has been sent
                import time
                time.sleep(2)
                
                # Start summary generation
                logger.info(f"Starting delayed summary generation for transcript of video {video.pk}")
                generate_summary(video.transcript.pk)
            except Exception as e:
                logger.exception(f"Error in delayed summary generation for video {video.pk}: {str(e)}")
        
        # Start delayed processing thread
        processing_thread = threading.Thread(
            target=delayed_summary_generation,
            daemon=True
        )
        processing_thread.start()
        
        messages.success(request, f"Generating summary for '{video.title or video.youtube_id}'. Please refresh in a few moments.")
    except Exception as e:
        logger.exception(f"Error generating summary for video {video.pk}: {str(e)}")
        messages.error(request, f"Error generating summary: {str(e)}")
    
    return redirect('video_detail', pk=video.pk)

@login_required
@require_POST
def delete_video(request, pk):
    """Delete a video and its associated data"""
    video = get_object_or_404(Video, pk=pk)
    
    # Check permission
    if not request.user.is_staff and video.user and video.user != request.user:
        raise PermissionDenied("You don't have permission to delete this video")
        
    video_title = video.title or video.youtube_id
    
    try:
        video.delete()
        messages.success(request, f"Video '{video_title}' has been deleted.")
        logger.info(f"Video {pk} ({video_title}) was deleted")
    except Exception as e:
        logger.exception(f"Error deleting video {pk}: {str(e)}")
        messages.error(request, f"Error deleting video: {str(e)}")
    
    return redirect('video_list')
