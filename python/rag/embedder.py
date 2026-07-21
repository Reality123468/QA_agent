import logging
import os
from typing import List

logger = logging.getLogger(__name__)

# Read API key/URL from env for OpenAI-compatible fallback
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

_embedder = None
_provider = None  # "deepseek", "huggingface", "sklearn"


class SklearnHashEmbedder:
    """
    A lightweight embedding fallback using sklearn's HashingVectorizer.
    Produces deterministic, fixed-size vectors without any model download.
    Does NOT require fitting — stateless and always produces the same dimension.
    """

    def __init__(self, n_features: int = 384):
        from sklearn.feature_extraction.text import HashingVectorizer

        self._vectorizer = HashingVectorizer(
            n_features=n_features,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        m = self._vectorizer.transform(texts)
        # Convert sparse CSR matrix rows to dense float lists
        return [m[i].toarray()[0].tolist() for i in range(m.shape[0])]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


def get_embedder():
    """
    Return an embedder instance with embed_documents() and embed_query() methods.

    Strategy (tried in order):
      1. DeepSeek API via OpenAIEmbeddings — fails at call time (no /embeddings endpoint).
      2. Local HuggingFace sentence-transformer — may fail on first download.
      3. Sklearn HashingVectorizer — guaranteed to work with no external deps.
    """
    global _embedder, _provider

    if _embedder is not None:
        return _embedder

    # Attempt 1: DeepSeek via OpenAI-compatible embeddings
    try:
        from langchain_openai import OpenAIEmbeddings

        _embedder = OpenAIEmbeddings(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_API_URL,
        )
        _provider = "deepseek"
        logger.info("Embedder initialized: DeepSeek API via OpenAIEmbeddings (model=deepseek-chat)")
        return _embedder
    except Exception as e:
        logger.warning(f"DeepSeek OpenAIEmbeddings init failed: {e}")

    # Attempt 2: Local HuggingFace sentence-transformer
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        _embedder = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        _provider = "huggingface"
        logger.info("Embedder initialized: local HuggingFace model (all-MiniLM-L6-v2, dim=384)")
        return _embedder
    except Exception as e:
        logger.warning(f"HuggingFace embedder init failed: {e}")

    # Attempt 3: Sklearn HashingVectorizer (always works)
    _embedder = SklearnHashEmbedder(n_features=384)
    _provider = "sklearn"
    logger.info("Embedder initialized: sklearn HashingVectorizer (n_features=384)")
    return _embedder


def embed_texts(texts: List[str]) -> List[List[float]]:
    """将文本列表转换为向量"""
    embedder = get_embedder()
    return embedder.embed_documents(texts)


def embed_query(query: str) -> List[float]:
    """将查询文本转换为向量"""
    embedder = get_embedder()
    return embedder.embed_query(query)


def get_vector_size() -> int:
    """Return the dimensionality of the current embedder."""
    get_embedder()
    if _provider == "deepseek":
        return 1536  # DeepSeek / OpenAI ada-002 class
    else:
        return 384  # all-MiniLM-L6-v2 / HashingVectorizer
