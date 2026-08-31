from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class HistoryMessage(BaseModel):
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: List[HistoryMessage] = []
    mode: Literal["rag", "agent", "search-only"] = "rag"
    summary: Optional[str] = None  # 累积对话摘要（滚动压缩），前端从 Conversation.summary 读取后传回


class ChatResponse(BaseModel):
    type: str  # thinking / answer / citation / thought / action / observation / downgrade / done / error
    content: str
    data: Optional[dict] = None
