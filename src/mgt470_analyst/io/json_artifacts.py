import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, RootModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, RootModel):
        return value.model_dump(mode="json")
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value


def write_json_artifact(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_jsonable(value), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json_artifact(path: Path, model_type: type[ModelT]) -> ModelT:
    return model_type.model_validate_json(path.read_text(encoding="utf-8"))
