import os as _os
# BGE-M3 is pre-downloaded; HuggingFace is blocked from China — skip all HF HTTP checks
for _key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
    _os.environ[_key] = "1"

import logging
from pathlib import Path

# Load .env from project root BEFORE any imports that read environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health_routes, agent_routes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="QA Agent - Python AI Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_routes.router, prefix="/api/agent", tags=["health"])
app.include_router(agent_routes.router, prefix="/api/agent", tags=["agent"])


@app.on_event("startup")
async def startup_event():
    import asyncio
    logger.info("QA Agent Python service starting up...")
    try:
        from rag import get_qdrant_client
        from rag import bm25_index
        qdrant = get_qdrant_client()
        bm25_index.rebuild_from_qdrant(qdrant)
    except Exception as e:
        logger.warning(f"BM25 rebuild on startup failed (non-fatal): {e}")

    # Pre-warm embedder so first request doesn't block on model download
    try:
        from rag.embedder import get_embedder
        loop = asyncio.get_running_loop()
        await asyncio.wait_for(
            loop.run_in_executor(None, get_embedder),
            timeout=60,
        )
    except asyncio.TimeoutError:
        logger.warning("Embedder pre-warm timed out after 60s (BGE-M3 download may be slow)")
    except Exception as e:
        logger.warning(f"Embedder pre-warm failed (non-fatal): {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
