"""Statement embeddings for semantic search (Phase C).

Uses Gemini's embedding model (default gemini-embedding-001) via the free lane — its quota
is separate from generateContent, so it works even when chat tagging is rate-capped.
Vectors are stored as JSON lists on Problem.embedding; ranking is plain cosine (fine at a
few-thousand rows). Provider is swappable via EMBEDDING_MODEL.
"""

import logging
import math
import os
from typing import List, Optional

# load .env before reading the key (mirrors gemini_client)
from dotenv import load_dotenv

load_dotenv()

import google.genai as genai

from .config import EMBEDDING_MODEL, GEMINI_API_KEY

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not set (needed for embeddings)")
        _client = genai.Client(api_key=key)
    return _client


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """Embed a batch of texts. Returns one vector (list of floats) per input."""
    if not texts:
        return []
    model = model or EMBEDDING_MODEL
    resp = _get_client().models.embed_content(model=model, contents=texts)
    return [list(e.values) for e in resp.embeddings]


def embed_query(text: str, model: Optional[str] = None) -> List[float]:
    """Embed a single query string."""
    return embed_texts([text], model=model)[0]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity of two equal-length vectors (0.0 if either is degenerate)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
