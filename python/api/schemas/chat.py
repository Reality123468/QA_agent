from pydantic import BaseModel, Field
from typing import List, Optional


class HistoryMessage(BaseModel):
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: List[HistoryMessage] = []


class ChatResponse(BaseModel):
    type: str  # thinking / answer / citation / done / error
    content: str
    data: Optional[dict] = None
