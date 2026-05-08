from typing import Literal

from pydantic import BaseModel, ConfigDict

Confidence = Literal["high", "medium", "low"]
Severity = Literal["high", "medium", "low"]


class ArtifactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
