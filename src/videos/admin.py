from django.contrib import admin
from .models import Video, Transcript

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'youtube_id', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('title', 'youtube_id', 'description')
    readonly_fields = ('youtube_id', 'created_at', 'updated_at', 'processing_time')
    fieldsets = (
        (None, {
            'fields': ('url', 'youtube_id', 'title', 'description')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Metadata', {
            'fields': ('duration', 'thumbnail_url', 'channel_name', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processing_time')
        }),
    )

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('video', 'language', 'is_auto_generated', 'word_count', 'created_at')
    list_filter = ('language', 'is_auto_generated')
    search_fields = ('video__youtube_id', 'video__title', 'content')
    readonly_fields = ('word_count', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('video', 'content')
        }),
        ('Metadata', {
            'fields': ('language', 'is_auto_generated')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'word_count')
        }),
    )
