"""
Tests for YouTube utilities module.
"""

from django.test import TestCase
from ..youtube_utils import extract_youtube_id, is_valid_youtube_id


class YouTubeUtilsTests(TestCase):
    """Test cases for YouTube utilities."""
    
    def test_extract_youtube_id_standard_url(self):
        """Test extracting ID from standard YouTube URL."""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        self.assertEqual(extract_youtube_id(url), 'dQw4w9WgXcQ')
    
    def test_extract_youtube_id_short_url(self):
        """Test extracting ID from YouTube short URL."""
        url = 'https://youtu.be/dQw4w9WgXcQ'
        self.assertEqual(extract_youtube_id(url), 'dQw4w9WgXcQ')
    
    def test_extract_youtube_id_shorts_url(self):
        """Test extracting ID from YouTube shorts URL."""
        url = 'https://youtube.com/shorts/dQw4w9WgXcQ'
        self.assertEqual(extract_youtube_id(url), 'dQw4w9WgXcQ')
    
    def test_extract_youtube_id_timestamp_url(self):
        """Test extracting ID from URL with timestamp."""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s'
        self.assertEqual(extract_youtube_id(url), 'dQw4w9WgXcQ')
    
    def test_extract_youtube_id_playlist_url(self):
        """Test extracting ID from playlist URL."""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLNCRTSKrIMmGtCGFMJyB7pW6q-rYOD8xM'
        self.assertEqual(extract_youtube_id(url), 'dQw4w9WgXcQ')
    
    def test_extract_youtube_id_embedded_url(self):
        """Test extracting ID from embedded player URL."""
        url = 'https://www.youtube.com/embed/dQw4w9WgXcQ'
        self.assertEqual(extract_youtube_id(url), 'dQw4w9WgXcQ')
    
    def test_extract_youtube_id_invalid_url(self):
        """Test extracting ID from invalid URL."""
        url = 'https://example.com/video123'
        self.assertIsNone(extract_youtube_id(url))
    
    def test_is_valid_youtube_id(self):
        """Test YouTube ID validation."""
        self.assertTrue(is_valid_youtube_id('dQw4w9WgXcQ'))
        self.assertFalse(is_valid_youtube_id('invalid-id'))
        self.assertFalse(is_valid_youtube_id(''))
        self.assertFalse(is_valid_youtube_id(None))
        self.assertFalse(is_valid_youtube_id('tooShort'))
        self.assertFalse(is_valid_youtube_id('wayTooLongYouTubeID123'))
        self.assertFalse(is_valid_youtube_id('invalid$chars'))