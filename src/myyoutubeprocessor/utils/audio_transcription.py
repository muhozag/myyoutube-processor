"""
Audio transcription utilities for YouTube videos without available transcripts.

This module provides functionality to download YouTube audio and transcribe it using
various speech-to-text services including OpenAI Whisper and Google Speech Recognition.
"""

import os
import tempfile
import logging
import time
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional imports with fallback handling
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    logger.warning("yt-dlp not available. Audio downloading will not work.")
    YT_DLP_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    USING_FASTER_WHISPER = True
except ImportError:
    try:
        import whisper
        WHISPER_AVAILABLE = True
        USING_FASTER_WHISPER = False
    except ImportError:
        logger.warning("Neither faster-whisper nor OpenAI Whisper available. Whisper transcription will not work.")
        WHISPER_AVAILABLE = False
        USING_FASTER_WHISPER = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    logger.warning("SpeechRecognition not available. Google Speech Recognition will not work.")
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    from pydub import AudioSegment
    from pydub.utils import which
    PYDUB_AVAILABLE = True
    # Check if ffmpeg is available
    FFMPEG_AVAILABLE = which("ffmpeg") is not None
    if not FFMPEG_AVAILABLE:
        logger.warning("ffmpeg not found. Audio processing capabilities will be limited.")
except ImportError:
    logger.warning("pydub not available. Audio processing will not work.")
    PYDUB_AVAILABLE = False
    FFMPEG_AVAILABLE = False


class AudioTranscriptionError(Exception):
    """Custom exception for audio transcription errors."""
    pass


class YouTubeAudioDownloader:
    """Handles downloading audio from YouTube videos."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the YouTube audio downloader.
        
        Args:
            output_dir: Directory to save downloaded audio files. If None, uses temp directory.
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        
    def download_audio(self, youtube_id: str, max_duration: int = 3600) -> Optional[str]:
        """
        Download audio from a YouTube video.
        
        Args:
            youtube_id: YouTube video ID
            max_duration: Maximum video duration in seconds (default: 1 hour)
            
        Returns:
            Path to the downloaded audio file, or None if download failed
            
        Raises:
            AudioTranscriptionError: If download fails or video is too long
        """
        if not YT_DLP_AVAILABLE:
            raise AudioTranscriptionError("yt-dlp is not available. Cannot download audio.")
        
        url = f"https://www.youtube.com/watch?v={youtube_id}"
        output_path = os.path.join(self.output_dir, f"{youtube_id}.%(ext)s")
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first to check duration
                info = ydl.extract_info(url, download=False)
                duration = info.get('duration', 0)
                
                if duration > max_duration:
                    raise AudioTranscriptionError(
                        f"Video too long ({duration}s > {max_duration}s). "
                        "Audio transcription is limited to shorter videos."
                    )
                
                logger.info(f"Downloading audio for video {youtube_id} (duration: {duration}s)")
                
                # Download the audio
                ydl.download([url])
                
                # Find the downloaded file
                wav_path = os.path.join(self.output_dir, f"{youtube_id}.wav")
                if os.path.exists(wav_path):
                    logger.info(f"Successfully downloaded audio to {wav_path}")
                    return wav_path
                else:
                    # Try to find any file with the youtube_id
                    for file in os.listdir(self.output_dir):
                        if youtube_id in file and file.endswith(('.wav', '.mp3', '.m4a')):
                            found_path = os.path.join(self.output_dir, file)
                            logger.info(f"Found downloaded audio at {found_path}")
                            return found_path
                    
                    raise AudioTranscriptionError(f"Downloaded audio file not found for {youtube_id}")
                    
        except Exception as e:
            logger.error(f"Error downloading audio for {youtube_id}: {str(e)}")
            raise AudioTranscriptionError(f"Failed to download audio: {str(e)}")


class AudioTranscriber:
    """Handles transcribing audio files using various speech-to-text services."""
    
    def __init__(self, whisper_model: str = "base", chunk_duration: int = 30):
        """
        Initialize the audio transcriber.
        
        Args:
            whisper_model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            chunk_duration: Duration in seconds for audio chunks when using SpeechRecognition
        """
        self.whisper_model = whisper_model
        self.chunk_duration = chunk_duration
        self._whisper_model_instance = None
        
    def _load_whisper_model(self):
        """Load Whisper model if not already loaded."""
        if not WHISPER_AVAILABLE:
            raise AudioTranscriptionError("Whisper is not available")
            
        if self._whisper_model_instance is None:
            logger.info(f"Loading Whisper model: {self.whisper_model}")
            try:
                if USING_FASTER_WHISPER:
                    # Use faster-whisper
                    self._whisper_model_instance = WhisperModel(self.whisper_model, device="cpu", compute_type="int8")
                else:
                    # Use original whisper
                    import whisper
                    self._whisper_model_instance = whisper.load_model(self.whisper_model)
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                raise AudioTranscriptionError(f"Failed to load Whisper model: {str(e)}")
                
        return self._whisper_model_instance
    
    def transcribe_with_whisper(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI Whisper or faster-whisper.
        
        Args:
            audio_path: Path to the audio file
            language: Language code (optional, auto-detected if None)
            
        Returns:
            Dictionary containing transcription results
        """
        model = self._load_whisper_model()
        
        logger.info(f"Transcribing audio with Whisper: {audio_path}")
        start_time = time.time()
        
        try:
            if USING_FASTER_WHISPER:
                # Use faster-whisper API
                segments, info = model.transcribe(audio_path, language=language)
                
                # Convert segments to list and extract text
                segments_list = list(segments)
                full_text = " ".join([segment.text for segment in segments_list])
                
                # Convert segments to dictionary format for compatibility
                segments_dict = [
                    {
                        'id': i,
                        'start': segment.start,
                        'end': segment.end,
                        'text': segment.text
                    }
                    for i, segment in enumerate(segments_list)
                ]
                
                elapsed_time = time.time() - start_time
                logger.info(f"Faster-Whisper transcription completed in {elapsed_time:.2f} seconds")
                
                return {
                    'text': full_text.strip(),
                    'language': info.language,
                    'segments': segments_dict,
                    'method': 'faster-whisper',
                    'model': self.whisper_model,
                    'processing_time': elapsed_time
                }
            else:
                # Use original whisper API
                result = model.transcribe(
                    audio_path,
                    language=language,
                    fp16=False,  # Use fp32 for better compatibility
                    verbose=False
                )
                
                elapsed_time = time.time() - start_time
                logger.info(f"Whisper transcription completed in {elapsed_time:.2f} seconds")
                
                return {
                    'text': result['text'].strip(),
                    'language': result.get('language', 'unknown'),
                    'segments': result.get('segments', []),
                    'method': 'whisper',
                    'model': self.whisper_model,
                    'processing_time': elapsed_time
                }
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {str(e)}")
            raise AudioTranscriptionError(f"Whisper transcription failed: {str(e)}")
    
    def transcribe_with_speech_recognition(self, audio_path: str, language: str = 'en-US') -> Dict[str, Any]:
        """
        Transcribe audio using Google Speech Recognition (via SpeechRecognition library).
        
        Args:
            audio_path: Path to the audio file
            language: Language code for recognition
            
        Returns:
            Dictionary containing transcription results
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            raise AudioTranscriptionError("SpeechRecognition is not available")
            
        if not PYDUB_AVAILABLE:
            raise AudioTranscriptionError("pydub is not available for audio processing")
        
        logger.info(f"Transcribing audio with Speech Recognition: {audio_path}")
        start_time = time.time()
        
        try:
            # Load and process audio
            audio = AudioSegment.from_file(audio_path)
            
            # Convert to wav if necessary and set to mono, 16kHz
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            # Split audio into chunks for better processing
            chunk_length_ms = self.chunk_duration * 1000
            chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
            
            recognizer = sr.Recognizer()
            full_transcription = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i + 1}/{len(chunks)}")
                
                # Save chunk to temporary file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    chunk.export(temp_file.name, format="wav")
                    
                    try:
                        # Recognize speech in chunk
                        with sr.AudioFile(temp_file.name) as source:
                            audio_data = recognizer.record(source)
                            text = recognizer.recognize_google(audio_data, language=language)
                            if text.strip():
                                full_transcription.append(text.strip())
                                
                    except sr.UnknownValueError:
                        logger.warning(f"Could not understand audio in chunk {i + 1}")
                    except sr.RequestError as e:
                        logger.error(f"Speech recognition request failed for chunk {i + 1}: {e}")
                    finally:
                        # Clean up temporary file
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
            
            # Combine all transcriptions
            full_text = " ".join(full_transcription)
            elapsed_time = time.time() - start_time
            
            logger.info(f"Speech Recognition transcription completed in {elapsed_time:.2f} seconds")
            
            return {
                'text': full_text,
                'language': language,
                'segments': [],  # Speech Recognition doesn't provide segments
                'method': 'speech_recognition',
                'model': 'google',
                'processing_time': elapsed_time,
                'chunks_processed': len(chunks),
                'chunks_transcribed': len(full_transcription)
            }
            
        except Exception as e:
            logger.error(f"Speech Recognition transcription failed: {str(e)}")
            raise AudioTranscriptionError(f"Speech Recognition transcription failed: {str(e)}")
    
    def transcribe(self, audio_path: str, language: Optional[str] = None, 
                  preferred_method: str = 'whisper') -> Dict[str, Any]:
        """
        Transcribe audio using the best available method.
        
        Args:
            audio_path: Path to the audio file
            language: Language code (optional)
            preferred_method: Preferred transcription method ('whisper' or 'speech_recognition')
            
        Returns:
            Dictionary containing transcription results
        """
        methods_to_try = []
        
        # Order methods based on preference and availability
        if preferred_method == 'whisper' and WHISPER_AVAILABLE:
            methods_to_try.append('whisper')
            if SPEECH_RECOGNITION_AVAILABLE:
                methods_to_try.append('speech_recognition')
        elif preferred_method == 'speech_recognition' and SPEECH_RECOGNITION_AVAILABLE:
            methods_to_try.append('speech_recognition')
            if WHISPER_AVAILABLE:
                methods_to_try.append('whisper')
        else:
            # Auto-select based on availability
            if WHISPER_AVAILABLE:
                methods_to_try.append('whisper')
            if SPEECH_RECOGNITION_AVAILABLE:
                methods_to_try.append('speech_recognition')
        
        if not methods_to_try:
            raise AudioTranscriptionError("No transcription methods available")
        
        last_error = None
        for method in methods_to_try:
            try:
                logger.info(f"Attempting transcription with {method}")
                
                if method == 'whisper':
                    return self.transcribe_with_whisper(audio_path, language)
                elif method == 'speech_recognition':
                    # Convert language code for Speech Recognition if needed
                    sr_language = language if language else 'en-US'
                    if language and '-' not in language:
                        # Convert ISO 639-1 to BCP 47 format
                        language_mapping = {
                            'en': 'en-US', 'es': 'es-ES', 'fr': 'fr-FR', 'de': 'de-DE',
                            'it': 'it-IT', 'pt': 'pt-BR', 'ru': 'ru-RU', 'ja': 'ja-JP',
                            'ko': 'ko-KR', 'zh': 'zh-CN', 'ar': 'ar-SA', 'hi': 'hi-IN',
                            'am': 'en-US'  # Amharic not supported, fallback to English
                        }
                        sr_language = language_mapping.get(language, 'en-US')
                    
                    return self.transcribe_with_speech_recognition(audio_path, sr_language)
                    
            except AudioTranscriptionError as e:
                last_error = e
                logger.warning(f"Transcription with {method} failed: {str(e)}")
                continue
        
        # If all methods failed
        raise AudioTranscriptionError(f"All transcription methods failed. Last error: {str(last_error)}")


def transcribe_youtube_audio(youtube_id: str, language: Optional[str] = None,
                           preferred_method: str = 'whisper',
                           max_duration: int = 3600,
                           cleanup: bool = True) -> Tuple[str, bool, str, Dict[str, Any]]:
    """
    Download and transcribe audio from a YouTube video.
    
    Args:
        youtube_id: YouTube video ID
        language: Language code for transcription (optional)
        preferred_method: Preferred transcription method ('whisper' or 'speech_recognition')
        max_duration: Maximum video duration in seconds
        cleanup: Whether to delete downloaded audio files after transcription
        
    Returns:
        Tuple of (transcript_text, is_auto_generated, detected_language, raw_data)
        
    Raises:
        AudioTranscriptionError: If transcription fails
    """
    downloader = YouTubeAudioDownloader()
    transcriber = AudioTranscriber()
    
    audio_path = None
    try:
        # Download audio
        logger.info(f"Starting audio transcription for YouTube video: {youtube_id}")
        audio_path = downloader.download_audio(youtube_id, max_duration)
        
        if not audio_path or not os.path.exists(audio_path):
            raise AudioTranscriptionError("Failed to download audio file")
        
        # Transcribe audio
        transcription_result = transcriber.transcribe(
            audio_path, 
            language=language, 
            preferred_method=preferred_method
        )
        
        transcript_text = transcription_result['text']
        detected_language = transcription_result['language']
        
        if not transcript_text.strip():
            raise AudioTranscriptionError("Transcription returned empty text")
        
        logger.info(f"Successfully transcribed audio for {youtube_id}: {len(transcript_text)} characters")
        
        # Format raw data for storage
        raw_data = {
            'method': transcription_result['method'],
            'model': transcription_result['model'],
            'processing_time': transcription_result['processing_time'],
            'segments': transcription_result.get('segments', []),
            'source': 'audio_transcription',
            'youtube_id': youtube_id
        }
        
        return transcript_text, True, detected_language, raw_data
        
    finally:
        # Cleanup downloaded audio file
        if cleanup and audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
                logger.info(f"Cleaned up audio file: {audio_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file {audio_path}: {str(e)}")


def is_audio_transcription_available() -> Dict[str, bool]:
    """
    Check which audio transcription methods are available.
    
    Returns:
        Dictionary indicating availability of each component
    """
    return {
        'yt_dlp': YT_DLP_AVAILABLE,
        'whisper': WHISPER_AVAILABLE,
        'speech_recognition': SPEECH_RECOGNITION_AVAILABLE,
        'pydub': PYDUB_AVAILABLE,
        'ffmpeg': FFMPEG_AVAILABLE,
        'any_available': any([WHISPER_AVAILABLE, SPEECH_RECOGNITION_AVAILABLE]) and YT_DLP_AVAILABLE
    }