"""
Command to clean up videos stuck in processing state for too long.
"""
import logging
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from videos.models import Video

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check for videos that have been stuck in processing state and mark them as failed'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', 
            type=int, 
            default=1,
            help='Mark videos as failed if they have been in processing state for more than this many hours (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report stuck videos without changing their status'
        )
    
    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        # Calculate cutoff time
        cutoff_time = timezone.now() - datetime.timedelta(hours=hours)
        
        # Find videos stuck in processing
        stuck_videos = Video.objects.filter(
            status='processing',
            updated_at__lt=cutoff_time
        )
        
        count = stuck_videos.count()
        self.stdout.write(f"Found {count} videos stuck in processing for more than {hours} hour(s)")
        
        if count > 0 and not dry_run:
            for video in stuck_videos:
                video.mark_failed(f"Processing timed out after {hours} hour(s)")
                self.stdout.write(f"Marked video {video.pk} ({video.youtube_id}) as failed")
                logger.info(f"Marked timed out video {video.pk} as failed")
        
        if dry_run and count > 0:
            self.stdout.write("Dry run - No videos were updated")
            for video in stuck_videos:
                self.stdout.write(f"  Would mark video {video.pk} ({video.youtube_id}) as failed")
        
        self.stdout.write(self.style.SUCCESS('Video status cleanup completed'))