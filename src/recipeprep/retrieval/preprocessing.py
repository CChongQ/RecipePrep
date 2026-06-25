"""Text normalization shared by ingredient retrieval workflows."""

import re

from nltk.stem import WordNetLemmatizer  # type: ignore[import-untyped]

_LEMMATIZER = WordNetLemmatizer()


def preprocess_text(text: str) -> str:
    """Lowercase, remove punctuation, and reduce words to a base form."""
    
    text = text.strip().lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(_LEMMATIZER.lemmatize(word) for word in text.split())
