import logging
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health_routes, agent_routes

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

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
    logger.info("QA Agent Python service starting up...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
