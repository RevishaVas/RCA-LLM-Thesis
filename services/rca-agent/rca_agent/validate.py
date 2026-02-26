from pydantic import BaseModel, Field
from typing import List

class RCAResult(BaseModel):
    root_cause: str = Field(..., description="Most likely root cause")
    evidence: List[str] = Field(default_factory=list, description="Evidence used")
    corrective_actions: List[str] = Field(default_factory=list)
    preventive_actions: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
