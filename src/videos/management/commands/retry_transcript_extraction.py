"""
Management command to retry processing videos that failed due to transcript issues.

This command is particularly useful for non-English videos (like Amharic) that may have
failed transcript extraction due to language detection or availability issues.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from videos.models import Video, Transcript
from videos.tasks import try_transcript_with_multiple_strategies, handle_video_without_transcript
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retry processing videos that failed due to transcript issues, especially non-English videos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--youtube-id',
            type=str,
            help='Specific YouTube video ID to retry (e.g., 1Zl4HxBLDs4)',
        )
        parser.add_argument(
            '--language',
            type=str,
            help='Specific language code to try (e.g., am for Amharic, ar for Arabic)',
        )
        parser.add_argument(
            '--all-failed',
            action='store_true',
            help='Retry all videos that failed due to transcript issues',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of videos to process (default: 50)',
        )

    def handle(self, *args, **options):
        youtube_id = options.get('youtube_id')
        language = options.get('language', 'auto')
        all_failed = options.get('all_failed')
        dry_run = options.get('dry_run')
        limit = options.get('limit')

        if not youtube_id and not all_failed:
            raise CommandError('You must specify either --youtube-id or --all-failed')

        if youtube_id:
            self.retry_single_video(youtube_id, language, dry_run)
        elif all_failed:
            self.retry_failed_videos(language, dry_run, limit)

    def retry_single_video(self, youtube_id, language, dry_run):
        """Retry processing a single video by YouTube ID."""
        try:
            video = Video.objects.get(youtube_id=youtube_id)
        except Video.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Video with YouTube ID {youtube_id} not found in database')
            )
            return

        self.stdout.write(f'Processing video: {youtube_id}')
        self.stdout.write(f'Current status: {video.processing_status}')
        self.stdout.write(f'Error message: {video.error_message}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: Would retry transcript extraction'))
            return

        self._process_video(video, language)

    def retry_failed_videos(self, language, dry_run, limit):
        """Retry processing all videos that failed due to transcript issues."""
        # Find videos that failed with transcript-related errors
        failed_videos = Video.objects.filter(
            processing_status='failed'
        ).filter(
            error_message__icontains='transcript'
        ).order_by('-created_at')[:limit]

        if not failed_videos:
            self.stdout.write(self.style.SUCCESS('No failed videos with transcript issues found'))
            return

        self.stdout.write(f'Found {len(failed_videos)} videos with transcript-related failures')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: Would process the following videos:'))
            for video in failed_videos:
                self.stdout.write(f'  - {video.youtube_id}: {video.error_message}')
            return

        processed = 0
        successful = 0
        
        for video in failed_videos:
            self.stdout.write(f'\nProcessing video {processed + 1}/{len(failed_videos)}: {video.youtube_id}')
            success = self._process_video(video, language)
            if success:
                successful += 1
            processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted processing {processed} videos. '
                f'Successfully processed: {successful}, '
                f'Still failed: {processed - successful}'
            )
        )

    def _process_video(self, video, language):
        """Process a single video with enhanced transcript extraction."""
        try:
            # Mark as processing
            video.processing_status = 'processing'
            video.processing_started_at = timezone.now()
            video.error_message = ''
            video.save()

            # Try enhanced transcript extraction
            success, transcript_result, error_msg = try_transcript_with_multiple_strategies(
                video.id, video.youtube_id
            )

            if success and transcript_result:
                transcript_text, is_auto_generated, language_code, raw_data = transcript_result

                # More lenient validation
                if not transcript_text or len(transcript_text.strip()) == 0:
                    error_msg = f"Transcript extraction returned empty content for {video.youtube_id}"
                    self.stdout.write(self.style.WARNING(error_msg))
                    return handle_video_without_transcript(video, error_msg)

                # Convert raw_data to serializable format
                serializable_data = None
                if raw_data:
                    try:
                        if isinstance(raw_data, list):
                            serializable_data = raw_data
                        else:
                            serializable_data = str(raw_data)
                    except Exception as e:
                        logger.warning(f"Could not serialize transcript data: {e}")

                # Save transcript
                transcript, created = Transcript.objects.update_or_create(
                    video=video,
                    defaults={
                        'content': transcript_text,
                        'language': language_code,
                        'is_auto_generated': is_auto_generated,
                        'raw_transcript_data': serializable_data
                    }
                )

                # Generate beautified content
                transcript.beautify_transcript(raw_data)

                # Try to generate summary
                try:
                    from myyoutubeprocessor.utils.ai.ai_service import get_ai_summary
                    summary = get_ai_summary(transcript_text)
                    if summary:
                        transcript.summary = summary
                        transcript.save(update_fields=['summary', 'updated_at'])
                        self.stdout.write(f'  ✓ Generated summary')
                    else:
                        self.stdout.write(f'  ⚠ Could not generate summary')
                except Exception as e:
                    self.stdout.write(f'  ⚠ Summary generation failed: {e}')

                # Mark as completed
                video.processing_status = 'completed'
                video.processing_completed_at = timezone.now()
                video.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Successfully processed {video.youtube_id} '
                        f'({language_code}, {len(transcript_text)} chars)'
                    )
                )
                return True

            else:
                # No transcript available - handle gracefully
                error_msg = error_msg or f"No transcript available for {video.youtube_id}"
                success = handle_video_without_transcript(video, error_msg)
                
                if success:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ No transcript available for {video.youtube_id}: {error_msg}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Failed to process {video.youtube_id}: {error_msg}'
                        )
                    )
                return success

        except Exception as e:
            error_msg = f"Error processing video: {str(e)}"
            video.processing_status = 'failed'
            video.error_message = error_msg
            video.save()
            
            self.stdout.write(
                self.style.ERROR(f'  ✗ Error processing {video.youtube_id}: {error_msg}')
            )
            return False

    def show_transcript_stats(self):
        """Show statistics about transcript availability."""
        total_videos = Video.objects.count()
        completed_videos = Video.objects.filter(processing_status='completed').count()
        failed_videos = Video.objects.filter(processing_status='failed').count()
        transcript_failures = Video.objects.filter(
            processing_status='failed',
            error_message__icontains='transcript'
        ).count()

        self.stdout.write('\n=== Transcript Processing Statistics ===')
        self.stdout.write(f'Total videos: {total_videos}')
        self.stdout.write(f'Successfully processed: {completed_videos}')
        self.stdout.write(f'Failed: {failed_videos}')
        self.stdout.write(f'Failed due to transcript issues: {transcript_failures}')

        # Show language breakdown if transcripts exist
        transcripts_with_language = Transcript.objects.exclude(language='').values_list('language', flat=True)
        if transcripts_with_language:
            from collections import Counter
            language_counts = Counter(transcripts_with_language)
            self.stdout.write('\nLanguage breakdown:')
            for lang, count in language_counts.most_common():
                self.stdout.write(f'  {lang}: {count} videos')