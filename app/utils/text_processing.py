import re
from collections import Counter
from typing import Dict


def extract_word_frequencies(text: str) -> Dict[str, int]:
    """
    Extract word frequencies from text.
    
    Args:
        text (str): The text to extract word frequencies from.
    
    Returns:
        Dict[str, int]: Dictionary mapping words to their counts.
    """
    # Convert to lowercase and split into words
    # Remove punctuation and non-alphanumeric characters
    words = re.findall(r'\b[a-z0-9]+\b', text.lower())
    
    # Count word frequencies
    word_counts = Counter(words)
    
    return dict(word_counts)
