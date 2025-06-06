from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from myyoutubeprocessor.utils.youtube_utils import extract_youtube_id, is_valid_youtube_id

class Video(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Processing'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    # Language choices for transcript extraction
    LANGUAGE_CHOICES = [
        ('auto', 'Auto-detect'),
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('pt', 'Portuguese'),
        ('ru', 'Russian'),
        ('it', 'Italian'),
        ('ja', 'Japanese'),
        ('ko', 'Korean'),
        ('zh', 'Chinese'),
        ('ar', 'Arabic'),
        ('hi', 'Hindi'),
        ('bn', 'Bengali'),
        ('ur', 'Urdu'),
        ('fa', 'Persian/Farsi'),
        ('th', 'Thai'),
        ('vi', 'Vietnamese'),
        ('tr', 'Turkish'),
        ('he', 'Hebrew'),
        ('am', 'Amharic'),
        ('sw', 'Swahili'),
        ('rw', 'Kinyarwanda'),
        ('ti', 'Tigrinya'),
        ('om', 'Oromo'),
        ('so', 'Somali'),
        ('ha', 'Hausa'),
        ('yo', 'Yoruba'),
        ('ig', 'Igbo'),
        ('ta', 'Tamil'),
        ('te', 'Telugu'),
        ('ml', 'Malayalam'),
        ('kn', 'Kannada'),
        ('gu', 'Gujarati'),
        ('mr', 'Marathi'),
        ('ne', 'Nepali'),
        ('si', 'Sinhala'),
        ('my', 'Myanmar/Burmese'),
        ('km', 'Khmer'),
        ('lo', 'Lao'),
        ('ka', 'Georgian'),
        ('hy', 'Armenian'),
        ('az', 'Azerbaijani'),
        ('kk', 'Kazakh'),
        ('ky', 'Kyrgyz'),
        ('uz', 'Uzbek'),
        ('tg', 'Tajik'),
        ('mn', 'Mongolian'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name="Uploaded by",
        null=True,  # Allow null for existing videos
        blank=True
    )
    
    url = models.URLField(
        verbose_name="YouTube URL",
        help_text="Enter a valid YouTube video URL"
    )
    youtube_id = models.CharField(
        max_length=11,
        unique=True,
        db_index=True,
        verbose_name="YouTube ID"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Video Title"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Video Description"
    )
    duration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration in seconds"
    )
    thumbnail_url = models.URLField(
        blank=True,
        verbose_name="Thumbnail URL"
    )
    channel_name = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name="Channel Name"
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Publication Date"
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='auto',
        verbose_name="Preferred Language",
        help_text="Select the expected language of the video to improve transcript accuracy"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True)
    processing_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Processing Started At"
    )
    processing_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Processing Completed At"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Video"
        verbose_name_plural = "Videos"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['youtube_id']),
        ]
    
    def __str__(self):
        return f"{self.title or self.youtube_id}"
    
    def clean(self):
        """Validate the video URL and ID"""
        if not self.youtube_id and self.url:
            self.youtube_id = extract_youtube_id(self.url)
        
        if not is_valid_youtube_id(self.youtube_id):
            raise ValidationError({"url": "Invalid YouTube URL or video ID"})
    
    def save(self, *args, **kwargs):
        """Extract and validate YouTube ID before saving"""
        if self.url and not self.youtube_id:
            self.youtube_id = extract_youtube_id(self.url)
            if not is_valid_youtube_id(self.youtube_id):
                raise ValueError("Invalid YouTube URL")
        super().save(*args, **kwargs)
    
    def mark_processing(self):
        """Mark the video as currently being processed"""
        self.status = 'processing'
        self.processing_started_at = timezone.now()
        self.save(update_fields=['status', 'processing_started_at', 'updated_at'])
    
    def mark_completed(self):
        """Mark the video as successfully processed"""
        self.status = 'completed'
        self.processing_completed_at = timezone.now()
        self.save(update_fields=['status', 'processing_completed_at', 'updated_at'])
    
    def mark_failed(self, error_message=""):
        """Mark the video as failed processing with error message"""
        self.status = 'failed'
        self.error_message = error_message
        self.processing_completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'processing_completed_at', 'updated_at'])
    
    @property
    def is_processed(self):
        """Check if the video has been successfully processed"""
        return self.status == 'completed'
    
    @property
    def processing_time(self):
        """Get the processing time if completed"""
        if self.status in ['completed', 'failed'] and self.processing_completed_at and self.processing_started_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        # Fallback to the old method if specific timestamps aren't available
        elif self.status in ['completed', 'failed'] and self.updated_at and self.created_at:
            return (self.updated_at - self.created_at).total_seconds()
        return None


class Transcript(models.Model):
    """Model to store video transcripts"""
    video = models.OneToOneField(
        Video, 
        on_delete=models.CASCADE, 
        related_name='transcript',
        verbose_name="Related Video"
    )
    content = models.TextField(
        verbose_name="Transcript Content"
    )
    beautified_content = models.TextField(
        blank=True,
        verbose_name="Beautified Transcript Content"
    )
    summary = models.TextField(
        blank=True,
        verbose_name="Transcript Summary"
    )
    content_word_count = models.IntegerField(
        default=0,
        verbose_name="Word Count"
    )
    raw_transcript_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Raw Transcript Data"
    )
    language = models.CharField(
        max_length=10, 
        default='en',
        verbose_name="Transcript Language"
    )
    is_auto_generated = models.BooleanField(
        default=True,
        verbose_name="Auto-generated Transcript"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Transcript"
        verbose_name_plural = "Transcripts"
        
    def __str__(self):
        return f"Transcript for {self.video}"
        
    def word_count(self):
        """Return the number of words in the transcript"""
        if self.content_word_count > 0:
            return self.content_word_count
        return len(self.content.split())
        
    def beautify_transcript(self, fetched_transcript=None):
        """
        Create a beautified version of the transcript from FetchedTranscript object or saved raw_transcript_data
        Returns the beautified content and also saves it to the model
        """
        data = fetched_transcript or self.raw_transcript_data
        
        if not data:
            return ""
            
        # Format the transcript with timestamps
        formatted_lines = []
        full_text = []
        
        # Handle different types of data
        if isinstance(data, list):
            # Standard list format with timestamps
            snippets = data
        elif hasattr(data, 'snippets'):
            # Object with snippets attribute
            snippets = data.snippets
        elif isinstance(data, str):
            # String data (probably a serialized object)
            # Just use the raw content for full text
            self.beautified_content = f"# Full Text\n\n{self.content}"
            self.save(update_fields=['beautified_content', 'updated_at'])
            return self.beautified_content
        else:
            # Unknown format
            try:
                snippets = list(data)  # Try to convert to a list
            except (TypeError, ValueError):
                snippets = []
        
        if not snippets:
            return ""
            
        for snippet in snippets:
            # Handle both object and dictionary formats
            if isinstance(snippet, dict):
                text = snippet.get('text', '')
                start = snippet.get('start', 0)
                duration = snippet.get('duration', 0)
            elif hasattr(snippet, 'text'):
                text = snippet.text
                start = getattr(snippet, 'start', 0)
                duration = getattr(snippet, 'duration', 0)
            else:
                # If we can't determine the format, convert to string
                text = str(snippet)
                start = 0
                duration = 0
                
            # Format timestamp as MM:SS
            minutes = int(start) // 60
            seconds = int(start) % 60
            timestamp = f"{minutes:02d}:{seconds:02d}"
            
            # Add formatted line
            if text and text.strip():  # Skip empty lines
                formatted_lines.append(f"[{timestamp}] {text}")
                full_text.append(text)
        
        # Create the beautified content with sections
        beautified = "# Timestamps and Text\n\n"
        beautified += "\n".join(formatted_lines)
        
        beautified += "\n\n# Full Text\n\n"
        beautified += " ".join(full_text)
        
        # Save the beautified content
        self.beautified_content = beautified
        self.save(update_fields=['beautified_content', 'updated_at'])
        
        return beautified

    def save(self, *args, **kwargs):
        """Override save to ensure beautified content is generated and word count is calculated"""
        is_new = not self.pk  # Check if this is a new record
        
        # Calculate word count before saving
        if self.content:
            self.content_word_count = len(self.content.split())
        
        # Call the standard save method
        super().save(*args, **kwargs)
        
        # If beautified_content is empty and we have raw_transcript_data, generate it
        if not self.beautified_content and self.raw_transcript_data:
            self.beautify_transcript()
