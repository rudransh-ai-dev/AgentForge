from pydantic import BaseModel

class Result(BaseModel):
    route: str
    result: str
