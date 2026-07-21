import os
from fastapi import Header, HTTPException, Depends


INTERNAL_API_KEY = os.getenv("AGENT_INTERNAL_API_KEY", "qa-agent-internal-api-key-2026")


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key
