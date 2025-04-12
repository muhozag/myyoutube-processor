"""
AI utilities module for interacting with Ollama models.
"""
import logging
import ollama
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def get_mistral_summary(text: str, max_length: int = 25000) -> Optional[str]:
    """
    Generate a summary of the given text using the Ollama Mistral-small3.1 model.
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model (to avoid token limits)
        
    Returns:
        A summary of the text, or None if an error occurred
    """
    try:
        # Trim text if needed to avoid exceeding token limits
        # 25000 characters is a safe estimate well within Mistral's context window
        if len(text) > max_length:
            # Get the first portion and the last portion to preserve context
            first_part = text[:int(max_length * 0.8)]
            last_part = text[-int(max_length * 0.2):]
            text = first_part + "\n...[content in the middle omitted for length]...\n" + last_part
            
        # Construct a prompt for summarization
        prompt = f"""
        You are a video summarization expert. Your task is to summarize the content of a video transcript.
        Please provide a concise summary of the following transcript.
        The summary should be structured and easy to read.
        The summary should be in English and should not include any personal opinions or interpretations.
        The summary should be suitable for someone who has not watched the video.
        Please include:
        1. The main topic and purpose of the video
        2. Key points and arguments presented
        3. Important facts, statistics, or examples mentioned
        4. Any conclusions or takeaways
        5. The overall structure of the presentation
        6. Timestamps for major topic transitions (if apparent from the transcript)

        Format the summary in clear paragraphs with appropriate headings for each section. 
        Keep the summary concise but include all essential information. 
        Aim for approximately 200-300 words depending on the video length and complexity.
        If the transcript appears to be truncated, summarize what is available:
        If the transcript appears to be truncated, summarize what is available:
        
        {text}
        
        Summary:
        """
        
        # Call the Ollama API with the mistral-small3.1 model
        response = ollama.chat(
            model='mistral-small3.1',
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.2,
                'num_predict': 1024,  # Increased to allow for more comprehensive summaries
            }
        )
        
        # Extract the summary from the response
        if response and 'message' in response and 'content' in response['message']:
            return response['message']['content'].strip()
        else:
            logger.error(f"Unexpected response format from Ollama: {response}")
            return None
    except Exception as e:
        logger.error(f"Error generating summary with Ollama: {str(e)}")
        return None