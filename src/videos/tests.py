from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import patch
from videos.models import Video
import datetime

class VideoModelTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.valid_id = "dQw4w9WgXcQ"
        self.valid_id2 = "dQw4w9WgXcD"  # Slightly different ID for second test
        self.valid_url2 = "https://www.youtube.com/watch?v=dQw4w9WgXcD"  # URL with different ID
        self.invalid_url = "https://www.youtube.com/watch?v=invalid"

    @patch('videos.models.extract_youtube_id')
    @patch('videos.models.is_valid_youtube_id')
    def test_video_creation_with_valid_url(self, mock_is_valid, mock_extract):
        """Test creating a video with valid URL"""
        mock_extract.return_value = self.valid_id
        mock_is_valid.return_value = True

        # Create a Video instance first without saving
        video = Video(
            url=self.valid_url,
            title="Test Video",
            description="Test Description"
        )
        # Then save it to trigger the save method properly
        video.save()
        
        self.assertEqual(video.youtube_id, self.valid_id)
        self.assertEqual(video.status, "pending")
        self.assertIsNotNone(video.created_at)
        self.assertIsNotNone(video.updated_at)
        mock_extract.assert_called_once_with(self.valid_url)
        mock_is_valid.assert_called_once_with(self.valid_id)

    @patch('myyoutubeprocessor.utils.youtube_utils.extract_youtube_id')
    @patch('myyoutubeprocessor.utils.youtube_utils.is_valid_youtube_id')
    def test_video_creation_with_invalid_url(self, mock_is_valid, mock_extract):
        """Test creating a video with invalid URL raises ValueError"""
        mock_extract.return_value = "invalid"
        mock_is_valid.return_value = False

        with self.assertRaises(ValueError):
            Video.objects.create(
                url=self.invalid_url,
                title="Invalid Video"
            )

    @patch('myyoutubeprocessor.utils.youtube_utils.is_valid_youtube_id')
    def test_clean_method_with_invalid_id(self, mock_is_valid):
        """Test clean method with invalid ID"""
        mock_is_valid.return_value = False
        
        video = Video(youtube_id="invalid")
        
        with self.assertRaises(ValidationError):
            video.clean()

    def test_mark_processing(self):
        """Test mark_processing method updates status correctly"""
        with patch('myyoutubeprocessor.utils.youtube_utils.extract_youtube_id') as mock_extract:
            with patch('myyoutubeprocessor.utils.youtube_utils.is_valid_youtube_id') as mock_is_valid:
                mock_extract.return_value = self.valid_id
                mock_is_valid.return_value = True
                
                video = Video.objects.create(url=self.valid_url)
                video.mark_processing()
                
                self.assertEqual(video.status, "processing")
                
                # Reload from database to verify
                updated_video = Video.objects.get(pk=video.pk)
                self.assertEqual(updated_video.status, "processing")

    def test_mark_completed(self):
        """Test mark_completed method updates status correctly"""
        with patch('myyoutubeprocessor.utils.youtube_utils.extract_youtube_id') as mock_extract:
            with patch('myyoutubeprocessor.utils.youtube_utils.is_valid_youtube_id') as mock_is_valid:
                mock_extract.return_value = self.valid_id
                mock_is_valid.return_value = True
                
                video = Video.objects.create(url=self.valid_url)
                video.mark_completed()
                
                self.assertEqual(video.status, "completed")
                
                # Reload from database to verify
                updated_video = Video.objects.get(pk=video.pk)
                self.assertEqual(updated_video.status, "completed")

    def test_mark_failed(self):
        """Test mark_failed method updates status and error_message correctly"""
        with patch('myyoutubeprocessor.utils.youtube_utils.extract_youtube_id') as mock_extract:
            with patch('myyoutubeprocessor.utils.youtube_utils.is_valid_youtube_id') as mock_is_valid:
                mock_extract.return_value = self.valid_id
                mock_is_valid.return_value = True
                
                error_msg = "Something went wrong"
                video = Video.objects.create(url=self.valid_url)
                video.mark_failed(error_msg)
                
                self.assertEqual(video.status, "failed")
                self.assertEqual(video.error_message, error_msg)
                
                # Reload from database to verify
                updated_video = Video.objects.get(pk=video.pk)
                self.assertEqual(updated_video.status, "failed")
                self.assertEqual(updated_video.error_message, error_msg)

    def test_is_processed_property(self):
        """Test is_processed property returns correct value"""
        with patch('myyoutubeprocessor.utils.youtube_utils.extract_youtube_id') as mock_extract:
            with patch('myyoutubeprocessor.utils.youtube_utils.is_valid_youtube_id') as mock_is_valid:
                mock_extract.return_value = self.valid_id
                mock_is_valid.return_value = True
                
                video = Video.objects.create(url=self.valid_url)
                self.assertFalse(video.is_processed)
                
                video.mark_completed()
                self.assertTrue(video.is_processed)
                
                video.mark_failed()
                self.assertFalse(video.is_processed)

    def test_processing_time_property(self):
        """Test processing_time property calculates correctly"""
        with patch('myyoutubeprocessor.utils.youtube_utils.extract_youtube_id') as mock_extract:
            with patch('myyoutubeprocessor.utils.youtube_utils.is_valid_youtube_id') as mock_is_valid:
                with patch('django.utils.timezone.now') as mock_now:
                    mock_extract.return_value = self.valid_id
                    mock_is_valid.return_value = True
                    
                    # Set up timestamps with known difference
                    start_time = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
                    end_time = datetime.datetime(2023, 1, 1, 12, 0, 30, tzinfo=datetime.timezone.utc)
                    
                    # First call (creation time)
                    mock_now.return_value = start_time
                    video = Video.objects.create(url=self.valid_url)
                    
                    # Second call (update time)
                    mock_now.return_value = end_time
                    video.mark_completed()
                    
                    # Processing time should be 30 seconds
                    self.assertEqual(video.processing_time, 30.0)
                    
                    # Test pending status
                    video.status = 'pending'
                    self.assertIsNone(video.processing_time)

    def test_str_representation(self):
        """Test string representation uses title or ID"""
        with patch('myyoutubeprocessor.utils.youtube_utils.extract_youtube_id') as mock_extract:
            with patch('myyoutubeprocessor.utils.youtube_utils.is_valid_youtube_id') as mock_is_valid:
                mock_extract.side_effect = [self.valid_id, self.valid_id2]
                mock_is_valid.return_value = True
                
                # With title
                video_with_title = Video.objects.create(
                    url=self.valid_url,
                    title="Test Video"
                )
                self.assertEqual(str(video_with_title), "Test Video")
                
                # Without title
                video_without_title = Video.objects.create(
                    url=self.valid_url2
                )
                video_without_title.title = ""
                video_without_title.save()
                self.assertEqual(str(video_without_title), self.valid_id2)
