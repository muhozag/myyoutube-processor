from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from django.db.models import Count, Avg, F, Case, When, IntegerField, Value
from django.template.response import TemplateResponse
from django.utils.text import format_lazy
from django.db.models.functions import Coalesce

class CustomAdminSite(admin.AdminSite):
    """
    Custom admin site that provides dashboard statistics
    """
    site_header = "YouTube Processor Admin"
    site_title = "YouTube Processor Admin Portal"
    index_title = "YouTube Processor Administration"
    
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        try:
            from videos.models import Video, Transcript
            
            # Get video statistics - improved query with error handling
            video_stats = Video.objects.aggregate(
                total=Count('id'),
                pending=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
                processing=Count(Case(When(status='processing', then=1), output_field=IntegerField())),
                completed=Count(Case(When(status='completed', then=1), output_field=IntegerField())),
                failed=Count(Case(When(status='failed', then=1), output_field=IntegerField())),
            )
            
            # Calculate processed percent
            total_videos = video_stats['total'] or 0
            completed_videos = video_stats['completed'] or 0
            processing_percent = round((completed_videos / total_videos) * 100) if total_videos > 0 else 0
            
            # Get transcript statistics
            transcript_stats = {
                'total': Transcript.objects.count(),
                'words_avg': int(Transcript.objects.aggregate(
                    avg=Coalesce(Avg(
                        Coalesce(F('content_word_count'), 
                                Value(0), 
                                output_field=IntegerField())
                    ), Value(0))
                )['avg'] or 0)
            }
            
            # Get recent videos
            recent_videos = Video.objects.all().order_by('-created_at')[:5]
            
            # Get user statistics
            user_stats = {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
                'staff': User.objects.filter(is_staff=True).count()
            }
            
            # Add to extra context
            extra_context.update({
                'video_count': video_stats['total'],
                'pending_count': video_stats['pending'],
                'processing_count': video_stats['processing'],
                'completed_count': video_stats['completed'],
                'failed_count': video_stats['failed'],
                'processing_percent': processing_percent,
                'transcript_count': transcript_stats['total'],
                'transcript_words_avg': transcript_stats['words_avg'],
                'recent_videos': recent_videos,
                'user_count': user_stats['total'],
                'active_users': user_stats['active'],
                'staff_users': user_stats['staff'],
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
                'processing_percent': 0,
                'transcript_count': 0,
                'transcript_words_avg': 0,
                'recent_videos': [],
                'user_count': 0,
                'active_users': 0,
                'staff_users': 0,
                'dashboard_error': str(e)
            })
        
        return super().index(request, extra_context)

# Create a custom admin site instance
custom_admin_site = CustomAdminSite(name='admin')

# Register the default User and Group admin
custom_admin_site.register(User, UserAdmin)
custom_admin_site.register(Group)

# Replace the default admin site with our custom one
admin.site = custom_admin_site
admin.sites.site = admin.site