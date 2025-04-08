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

from .models import Video, Transcript
from .forms import VideoSubmissionForm
from .tasks import process_video_async, generate_summary

# Set up logger
logger = logging.getLogger(__name__)

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
        # Add additional context here if needed
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
            
            # Start processing in background thread
            # In production, this would be handled by Celery
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
        
        # Start processing in background thread
        # In production, this would be handled by Celery
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
        
        # Start summary generation in background thread
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
