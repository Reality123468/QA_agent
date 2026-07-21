from pydantic import BaseModel, Field
from typing import Optional


class DocumentInfo(BaseModel):
    id: int
    title: str
    file_path: str
    file_type: str
    department: str = "全部"
    security_level: str = "内部"


class IndexRequest(BaseModel):
    document: DocumentInfo
    callback_url: Optional[str] = None
