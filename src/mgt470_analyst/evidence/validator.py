from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from mgt470_analyst.evidence.store import EvidenceStore


@dataclass
class ValidationResult:
    ok: bool
    missing_ids: list[str] = field(default_factory=list)


def _as_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def collect_evidence_ids(value: Any) -> list[str]:
    data = _as_data(value)
    found: list[str] = []
    if isinstance(data, dict):
        for key, nested in data.items():
            if key == "evidence_ids" and isinstance(nested, list):
                found.extend(str(item) for item in nested)
            elif key == "evidence_id" and nested:
                found.append(str(nested))
            else:
                found.extend(collect_evidence_ids(nested))
    elif isinstance(data, list):
        for item in data:
            found.extend(collect_evidence_ids(item))
    return found


def _replace_missing_id(value: Any, missing_id: str, replacement_id: str) -> Any:
    data = _as_data(value)
    if isinstance(data, dict):
        replaced: dict[str, Any] = {}
        for key, nested in data.items():
            if key == "evidence_ids" and isinstance(nested, list):
                replaced[key] = [replacement_id if item == missing_id else item for item in nested]
            elif key == "evidence_id" and nested == missing_id:
                replaced[key] = replacement_id
            else:
                replaced[key] = _replace_missing_id(nested, missing_id, replacement_id)
        return replaced
    if isinstance(data, list):
        return [_replace_missing_id(item, missing_id, replacement_id) for item in data]
    return data


def validate_and_repair_evidence(
    artifact: Any, store: EvidenceStore, module_name: str
) -> tuple[Any, ValidationResult]:
    data = _as_data(artifact)
    missing = [
        evidence_id
        for evidence_id in collect_evidence_ids(data)
        if evidence_id not in store.items
    ]
    for evidence_id in collect_evidence_ids(data):
        if evidence_id in store.items:
            store.mark_used(evidence_id, module_name)

    for missing_id in missing:
        replacement = _find_existing_claim_match(data, store)
        if replacement is None:
            replacement = store.add_claim(
                claim=_claim_for_repair(data),
                source_id="S0",
                locator="repair pass",
                claim_type="assumption",
                confidence="low",
                used_by_modules=[module_name],
            )
        else:
            store.mark_used(replacement.id, module_name)
        data = _replace_missing_id(data, missing_id, replacement.id)

    remaining = [
        evidence_id
        for evidence_id in collect_evidence_ids(data)
        if evidence_id not in store.items
    ]
    for evidence_id in collect_evidence_ids(data):
        if evidence_id in store.items:
            store.mark_used(evidence_id, module_name)
    return data, ValidationResult(ok=not remaining, missing_ids=remaining)


def _claim_for_repair(data: Any) -> str:
    if isinstance(data, dict) and isinstance(data.get("claim"), str):
        return data["claim"]
    return "Deterministic repair assumption for an artifact claim missing evidence."


def _find_existing_claim_match(data: Any, store: EvidenceStore):
    claim_texts = set(_collect_claim_texts(data))
    for item in store.items.values():
        if item.claim in claim_texts:
            return item
    return None


def _collect_claim_texts(value: Any) -> list[str]:
    data = _as_data(value)
    claims: list[str] = []
    if isinstance(data, dict):
        claim = data.get("claim")
        if isinstance(claim, str):
            claims.append(claim)
        for nested in data.values():
            claims.extend(_collect_claim_texts(nested))
    elif isinstance(data, list):
        for item in data:
            claims.extend(_collect_claim_texts(item))
    return claims
