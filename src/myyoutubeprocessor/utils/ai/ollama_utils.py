"""
AI utilities module for interacting with Ollama models.
"""
import logging
import ollama
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def get_mistral_summary(text: str, max_length: int = 1000) -> Optional[str]:
    """
    Generate a summary of the given text using the Ollama Mistral-small model.
    
    Args:
        text: The text to summarize
        max_length: The maximum length of text to send to the model (to avoid token limits)
    
    Returns:
        A summary of the text, or None if an error occurred
    """
    try:
        # Trim text if needed to avoid exceeding token limits
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        # Construct a prompt for summarization
        prompt = f"""
Please provide a concise summary of the following transcript. 
Focus on the main topics discussed and key points:

{text}

Summary:
"""
        
        # Call the Ollama API with the mistral-small:22b model
        response = ollama.chat(
            model='mistral-small:22b',
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.2,
                'num_predict': 512,
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