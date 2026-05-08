from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel
from mgt470_analyst.schemas.raw_input import RawInput


class ModuleRun(ArtifactModel):
    module: str
    module_version: str = "0.1.0"
    input_hash: str
    output_path: str
    status: Literal["ok", "error"]
    error: str | None = None


class RunManifest(ArtifactModel):
    run_id: str
    created_at: str
    input: RawInput
    artifacts: dict[str, str] = Field(default_factory=dict)
    modules: list[ModuleRun] = Field(default_factory=list)
