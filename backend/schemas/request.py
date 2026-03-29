from pydantic import BaseModel

class Query(BaseModel):
    prompt: str

class NodeQuery(BaseModel):
    agent_id: str
    prompt: str
