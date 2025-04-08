#!/usr/bin/env python
"""
Debug script to test transcript extraction for a specific YouTube video.

Usage:
    python debug_transcript.py <youtube_video_id>
    
Example:
    python debug_transcript.py dQw4w9WgXcQ
"""

import sys
import logging
import pprint
from myyoutubeprocessor.utils.youtube_utils import extract_transcript, extract_youtube_id

# Configure logging to display detailed information
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def main():
    # Get the YouTube ID from command line or prompt
    if len(sys.argv) > 1:
        input_value = sys.argv[1]
    else:
        input_value = input("Enter YouTube URL or video ID: ")
    
    # Check if it's a URL or an ID
    if "youtube.com" in input_value or "youtu.be" in input_value:
        youtube_id = extract_youtube_id(input_value)
        if not youtube_id:
            print(f"Error: Could not extract YouTube ID from URL: {input_value}")
            return
    else:
        youtube_id = input_value
    
    print(f"\nAttempting to extract transcript for YouTube ID: {youtube_id}\n")
    
    # Try to extract transcript with multiple language codes
    language_codes = ['en', 'en-US', 'en-GB', 'auto']
    
    print("Testing with different language codes:")
    for lang in language_codes:
        print(f"\n--- Testing with language code: {lang} ---")
        transcript_text, is_auto_generated, actual_language = extract_transcript(youtube_id, lang)
        
        if transcript_text:
            print(f"✅ SUCCESS! Found transcript in language: {actual_language}")
            print(f"Auto-generated: {is_auto_generated}")
            print(f"Transcript preview (first 150 chars): {transcript_text[:150]}...")
            print(f"Length: {len(transcript_text)} characters, ~{len(transcript_text.split())} words")
        else:
            print(f"❌ FAILED to extract transcript with language code: {lang}")
    
    # Now try using the YouTube Transcript API directly
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        print("\n--- Trying direct API access ---")
        available_transcripts = YouTubeTranscriptApi.list_transcripts(youtube_id)
        print("Available transcripts:")
        for transcript in available_transcripts:
            print(f" - {transcript.language_code} ({'Auto-generated' if transcript.is_generated else 'Manual'})")
        
        # Try to fetch the first available transcript
        try:
            first_transcript = list(available_transcripts)[0]
            transcript_data = first_transcript.fetch()
            print(f"\nSuccessfully fetched transcript in {first_transcript.language_code}")
            
            # Examine the transcript data structure
            print("\nExamining transcript data structure:")
            if hasattr(transcript_data, '__iter__') and not isinstance(transcript_data, str):
                print(f"Transcript data is iterable of type: {type(transcript_data)}")
                if len(transcript_data) > 0:
                    print("\nFirst item in transcript data:")
                    pprint.pprint(transcript_data[0] if isinstance(transcript_data, list) else "Not subscriptable")
                    print(f"\nTotal items: {len(transcript_data)}")
            elif hasattr(transcript_data, 'text'):
                print(f"Transcript data has 'text' attribute of type: {type(transcript_data)}")
                print(f"\nText preview: {transcript_data.text[:150]}...")
            else:
                print(f"Transcript data type: {type(transcript_data)}")
                print(f"Attributes: {dir(transcript_data)[:10]}...")
        
        except Exception as e:
            print(f"Error examining transcript: {str(e)}")
            
    except Exception as e:
        print(f"\nError accessing transcripts directly: {str(e)}")

if __name__ == "__main__":
    main()