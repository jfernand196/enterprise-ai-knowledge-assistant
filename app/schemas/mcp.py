from pydantic import BaseModel


class McpToolResponse(BaseModel):
    name: str
    description: str
    input_schema: dict
    source: str
