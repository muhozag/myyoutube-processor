from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Video, Transcript
# Import the custom admin site
from myyoutubeprocessor.admin import custom_admin_site

def mark_videos_as_pending(modeladmin, request, queryset):
    queryset.update(status='pending', error_message='')
mark_videos_as_pending.short_description = "Mark selected videos as pending"

def mark_videos_as_failed(modeladmin, request, queryset):
    queryset.update(status='failed', error_message='Manually marked as failed')
mark_videos_as_failed.short_description = "Mark selected videos as failed"

# Define admin classes without using the decorator
class VideoAdmin(admin.ModelAdmin):
    list_display = ('video_thumbnail', 'title', 'youtube_id', 'status_badge', 'user_link', 'has_transcript', 'created_at', 'updated_at')
    list_filter = ('status', 'user', 'created_at', 'updated_at')
    search_fields = ('title', 'youtube_id', 'description', 'channel_name', 'user__username', 'user__email')
    readonly_fields = ('youtube_id', 'created_at', 'updated_at', 'processing_time', 'video_embed', 'transcript_link')
    actions = [mark_videos_as_pending, mark_videos_as_failed]
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('url', 'youtube_id', 'title', 'description', 'user')
        }),
        ('Video Preview', {
            'fields': ('video_embed',),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'transcript_link')
        }),
        ('Metadata', {
            'fields': ('duration', 'thumbnail_url', 'channel_name', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processing_time')
        }),
    )
    
    def video_thumbnail(self, obj):
        if obj.thumbnail_url:
            return format_html('<img src="{}" width="120" height="68" style="border-radius: 5px;" />', obj.thumbnail_url)
        return "No thumbnail"
    video_thumbnail.short_description = "Thumbnail"
    
    def status_badge(self, obj):
        status_colors = {
            'pending': '#f39c12',
            'processing': '#3498db',
            'completed': '#2ecc71',
            'failed': '#e74c3c'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 5px;">{}</span>',
            status_colors.get(obj.status, '#777'),
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def user_link(self, obj):
        if obj.user:
            user_url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', user_url, obj.user.username)
        return "No user"
    user_link.short_description = "User"
    
    def video_embed(self, obj):
        if obj.youtube_id:
            embed_code = (
                f'<iframe width="560" height="315" '
                f'src="https://www.youtube.com/embed/{obj.youtube_id}" '
                f'frameborder="0" allowfullscreen></iframe>'
            )
            return mark_safe(embed_code)
        return "No YouTube ID available"
    video_embed.short_description = "Video Preview"
    
    def has_transcript(self, obj):
        try:
            if hasattr(obj, 'transcript'):
                return True
            return False
        except:
            return False
    has_transcript.boolean = True
    has_transcript.short_description = "Has Transcript"
    
    def transcript_link(self, obj):
        try:
            if hasattr(obj, 'transcript'):
                transcript_url = reverse('admin:videos_transcript_change', args=[obj.transcript.id])
                return format_html('<a href="{}">{}</a>', transcript_url, "View Transcript")
            return "No transcript available"
        except:
            return "No transcript available"
    transcript_link.short_description = "Transcript"

class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('video_link', 'user_info', 'language', 'is_auto_generated', 'word_count', 'created_at')
    list_filter = ('language', 'is_auto_generated', 'video__user', 'created_at', 'updated_at')
    search_fields = ('video__youtube_id', 'video__title', 'content', 'summary', 'video__user__username')
    readonly_fields = ('word_count', 'created_at', 'updated_at', 'video_link', 'video_embed', 'user_info')
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('video', 'video_link', 'user_info')
        }),
        ('Video Preview', {
            'fields': ('video_embed',),
            'classes': ('collapse',),
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',),
        }),
        ('Processed Content', {
            'fields': ('beautified_content', 'summary'),
            'classes': ('wide',),
        }),
        ('Metadata', {
            'fields': ('language', 'is_auto_generated', 'raw_transcript_data'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'word_count')
        }),
    )
    
    def video_link(self, obj):
        if obj.video:
            video_url = reverse('admin:videos_video_change', args=[obj.video.id])
            return format_html('<a href="{}">{}</a>', video_url, obj.video.title or obj.video.youtube_id)
        return "No video associated"
    video_link.short_description = "Video"
    
    def user_info(self, obj):
        if obj.video and obj.video.user:
            user_url = reverse('admin:auth_user_change', args=[obj.video.user.id])
            return format_html('<a href="{}">{}</a>', user_url, obj.video.user.username)
        return "No user"
    user_info.short_description = "User"
    
    def video_embed(self, obj):
        if obj.video and obj.video.youtube_id:
            embed_code = (
                f'<iframe width="560" height="315" '
                f'src="https://www.youtube.com/embed/{obj.video.youtube_id}" '
                f'frameborder="0" allowfullscreen></iframe>'
            )
            return mark_safe(embed_code)
        return "No YouTube ID available"
    video_embed.short_description = "Video Preview"

# Register with the custom admin site
custom_admin_site.register(Video, VideoAdmin)
custom_admin_site.register(Transcript, TranscriptAdmin)
