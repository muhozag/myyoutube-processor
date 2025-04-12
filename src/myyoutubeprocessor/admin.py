from django.contrib import admin
from django.db.models import Count, Avg, F, Case, When, IntegerField, Value
from django.template.response import TemplateResponse
from django.utils.text import format_lazy
from django.db.models.functions import Coalesce

class CustomAdminSite(admin.AdminSite):
    """
    Custom admin site that provides dashboard statistics
    """
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        try:
            from videos.models import Video, Transcript
            
            # Get video statistics
            video_stats = Video.objects.aggregate(
                total=Count('id'),
                pending=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
                processing=Count(Case(When(status='processing', then=1), output_field=IntegerField())),
                completed=Count(Case(When(status='completed', then=1), output_field=IntegerField())),
                failed=Count(Case(When(status='failed', then=1), output_field=IntegerField())),
            )
            
            # Get transcript statistics
            transcript_stats = {
                'total': Transcript.objects.count(),
                'words_avg': int(Transcript.objects.aggregate(
                    avg=Coalesce(Avg(
                        Coalesce(F('content_word_count'), Value(0), output_field=IntegerField())
                    ), Value(0))
                )['avg'] or 0)
            }
            
            # Get recent videos
            recent_videos = Video.objects.all().order_by('-created_at')[:5]
            
            # Add to extra context
            extra_context.update({
                'video_count': video_stats['total'],
                'pending_count': video_stats['pending'],
                'processing_count': video_stats['processing'],
                'completed_count': video_stats['completed'],
                'failed_count': video_stats['failed'],
                'transcript_count': transcript_stats['total'],
                'transcript_words_avg': transcript_stats['words_avg'],
                'recent_videos': recent_videos,
            })
        except Exception as e:
            import logging
            logger = logging.getLogger('myyoutubeprocessor')
            logger.error(f"Error generating admin dashboard: {e}")
            
            # Provide empty defaults if there's an error
            extra_context.update({
                'video_count': 0,
                'pending_count': 0,
                'processing_count': 0,
                'completed_count': 0,
                'failed_count': 0,
                'transcript_count': 0,
                'transcript_words_avg': 0,
                'recent_videos': [],
                'dashboard_error': str(e)
            })
        
        return super().index(request, extra_context)


# Create a custom admin site instance
custom_admin_site = CustomAdminSite(name='custom_admin')