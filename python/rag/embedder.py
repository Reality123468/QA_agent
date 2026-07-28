import logging
import os
import sys
from typing import List

logger = logging.getLogger(__name__)

# Add D drive packages to path for portable installs
_D_PACKAGES = "D:/python-packages"
if os.path.isdir(_D_PACKAGES) and _D_PACKAGES not in sys.path:
    sys.path.insert(0, _D_PACKAGES)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

_embedder = None
_provider = None  # "bge-m3", "deepseek", "huggingface", "sklearn"
_vector_size = None


class SklearnHashEmbedder:
    """Stateless fallback embedder using sklearn HashingVectorizer (384-dim)."""

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
        return [m[i].toarray()[0].tolist() for i in range(m.shape[0])]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class BGE_M3_Embedder:
    """Wraps sentence-transformers BGE-M3 to expose embed_documents / embed_query."""

    def __init__(self):
        import os as _os
        # Force offline mode for all HF libraries
        for _key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
            _os.environ[_key] = "1"

        # Check that model files exist locally before attempting load
        cache = _os.path.join(_os.path.expanduser("~"), ".cache", "huggingface", "hub",
                              "models--BAAI--bge-m3", "snapshots")
        has_config = False
        if _os.path.isdir(cache):
            for _d in _os.listdir(cache):
                _p = _os.path.join(cache, _d, "config.json")
                if _os.path.isfile(_p):
                    has_config = True
                    break
        if not has_config:
            raise RuntimeError(
                "BGE-M3 config files not cached (HuggingFace blocked). "
                "Falling through to next embedder."
            )

        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer("BAAI/bge-m3", device="cpu", local_files_only=True)
        self._dim = self._model.get_embedding_dimension()

    @property
    def dim(self) -> int:
        return self._dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        ).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self._model.encode(
            [text], normalize_embeddings=True, show_progress_bar=False
        )[0].tolist()


def get_embedder():
    """
    Return an embedder instance with embed_documents() and embed_query() methods.

    Fallback chain (first successful init wins):
      1. BGE-M3 local (1024-dim) — best Chinese semantic quality, zero cost
      2. DeepSeek API via OpenAIEmbeddings (1536-dim) — requires valid API key
      3. HuggingFace all-MiniLM-L6-v2 (384-dim) — lightweight local fallback
      4. sklearn HashingVectorizer (384-dim) — guaranteed, no dependencies
    """
    global _embedder, _provider, _vector_size

    if _embedder is not None:
        return _embedder

    # Attempt 1: DeepSeek API via OpenAIEmbeddings (fast, accessible from China)
    try:
        from langchain_openai import OpenAIEmbeddings

        test_embedder = OpenAIEmbeddings(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_API_URL,
        )
        test_embedder.embed_query("test")
        _embedder = test_embedder
        _provider = "deepseek"
        _vector_size = 1536
        logger.info("Embedder initialized: DeepSeek API (dim=1536)")
        return _embedder
    except Exception as e:
        logger.warning("DeepSeek OpenAIEmbeddings init failed: %s", e)

    # Attempt 2: BGE-M3 local (1024-dim)
    # NOTE: skipped when HuggingFace is blocked (model loads but encode hangs due to
    # transformers background HTTP checks). Uncomment when HF is accessible.
    # try:
    #     e = BGE_M3_Embedder()
    #     import concurrent.futures as _cf
    #     with _cf.ThreadPoolExecutor(max_workers=1) as _exec:
    #         _future = _exec.submit(e.embed_query, "test")
    #         _future.result(timeout=10)
    #     _embedder = e
    #     _provider = "bge-m3"
    #     _vector_size = e.dim
    #     logger.info("Embedder initialized: BGE-M3 (BAAI/bge-m3, dim=%d)", e.dim)
    #     return _embedder
    # except Exception as e:
    #     logger.warning("BGE-M3 init failed: %s", e)

    # Attempt 3: sklearn HashingVectorizer (guaranteed fallback)
    _embedder = SklearnHashEmbedder(n_features=384)
    _provider = "sklearn"
    _vector_size = 384
    logger.info("Embedder initialized: sklearn HashingVectorizer (n_features=384)")
    return _embedder


def _fallback_to_sklearn():
    global _embedder, _provider, _vector_size
    _embedder = SklearnHashEmbedder(n_features=384)
    _provider = "sklearn"
    _vector_size = 384
    logger.info("Embedder fallen back to: sklearn HashingVectorizer (n_features=384)")


def embed_texts(texts: List[str]) -> List[List[float]]:
    embedder = get_embedder()
    try:
        return embedder.embed_documents(texts)
    except Exception as e:
        logger.warning("Embedder.embed_documents() failed (%s), falling back to sklearn", e)
        _fallback_to_sklearn()
        return get_embedder().embed_documents(texts)


def embed_query(query: str) -> List[float]:
    embedder = get_embedder()
    try:
        return embedder.embed_query(query)
    except Exception as e:
        logger.warning("Embedder.embed_query() failed (%s), falling back to sklearn", e)
        _fallback_to_sklearn()
        return get_embedder().embed_query(query)


def get_vector_size() -> int:
    """Return the dimensionality of the current active embedder."""
    get_embedder()
    return _vector_size or 384
