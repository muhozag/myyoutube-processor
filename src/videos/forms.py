from django import forms
from .models import Video

class VideoSubmissionForm(forms.ModelForm):
    """Form for submitting a YouTube video for processing"""
    
    class Meta:
        model = Video
        fields = ['url', 'title', 'description', 'preferred_language']
        widgets = {
            'url': forms.URLInput(attrs={'placeholder': 'Enter YouTube URL'}),
            'title': forms.TextInput(attrs={'placeholder': 'Video title (optional)'}),
            'description': forms.Textarea(attrs={
                'placeholder': 'Video description (optional)',
                'rows': 4
            }),
            'preferred_language': forms.Select(attrs={
                'class': 'form-select',
                'title': 'Select the expected language of the video to improve transcript accuracy'
            }),
        }
        help_texts = {
            'url': 'Enter a valid YouTube video URL (e.g., https://www.youtube.com/watch?v=...).',
            'title': 'Leave blank to use the YouTube video title (will be fetched later)',
            'description': 'Leave blank to use the YouTube video description (will be fetched later)',
            'preferred_language': 'Select the expected language of the video. Auto-detect will try to find the best available transcript.',
        }

    def clean_url(self):
        """Validate the URL is a proper YouTube URL"""
        url = self.cleaned_data.get('url')
        
        # Basic validation happens in the model's save method
        # Additional validation could be added here if needed
        
        return url