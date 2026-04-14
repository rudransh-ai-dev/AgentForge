from pydantic import BaseModel
from typing import Optional

class Query(BaseModel):
    prompt: str

class NodeQuery(BaseModel):
    agent_id: str
    prompt: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
