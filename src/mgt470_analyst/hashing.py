import hashlib
import json
from typing import Any

from mgt470_analyst.io.json_artifacts import to_jsonable


def stable_hash(value: Any) -> str:
    payload = json.dumps(
        to_jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
