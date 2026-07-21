# RAG module: Retrieval-Augmented Generation
# Handles document loading, chunking, embedding, indexing, and hybrid retrieval.

import os
import logging
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

# Qdrant storage configuration
# When Docker Qdrant is available, prefer it (localhost:6333 = gRPC).
# Otherwise, fall back to local in-memory mode (no server needed).
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

_qdrant_client = None


def get_qdrant_client() -> QdrantClient:
    """Return a singleton QdrantClient, preferring remote server, falling back to local in-memory."""
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client

    # Try remote Qdrant server first
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=5)
        client.get_collections()  # health check
        _qdrant_client = client
        logger.info(f"Connected to Qdrant server at {QDRANT_HOST}:{QDRANT_PORT}")
        return _qdrant_client
    except Exception:
        logger.warning(
            f"Cannot connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}. "
            f"Falling back to local in-memory storage."
        )
        _qdrant_client = QdrantClient(location=":memory:")
        return _qdrant_client
