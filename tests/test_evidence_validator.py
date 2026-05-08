from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.evidence.validator import collect_evidence_ids, validate_and_repair_evidence
from mgt470_analyst.schemas.raw_input import RawInput


def test_collect_evidence_ids_from_nested_dicts() -> None:
    artifact = {
        "evidence_ids": ["E1"],
        "nested": [{"evidence_id": "E2"}, {"other": "x"}],
    }

    assert collect_evidence_ids(artifact) == ["E1", "E2"]


def test_validator_updates_used_by_modules_for_valid_ids() -> None:
    store = EvidenceStore.from_raw_input(RawInput(company_name="Duolingo"))
    artifact = {"evidence_ids": ["E1"]}

    repaired, result = validate_and_repair_evidence(artifact, store, module_name="company_profile")

    assert result.ok
    assert repaired["evidence_ids"] == ["E1"]
    assert "company_profile" in store.items["E1"].used_by_modules


def test_validator_repairs_missing_ids_with_low_confidence_assumption() -> None:
    store = EvidenceStore.from_raw_input(RawInput(company_name="Duolingo"))
    artifact = {"claim": "New unsupported claim", "evidence_ids": ["E999"]}

    repaired, result = validate_and_repair_evidence(artifact, store, module_name="weak_links")

    assert result.ok
    assert repaired["evidence_ids"] != ["E999"]
    new_id = repaired["evidence_ids"][0]
    assert new_id in store.items
    assert store.items[new_id].claim_type == "assumption"
    assert store.items[new_id].confidence == "low"


def test_validator_repairs_missing_id_by_matching_existing_claim_text() -> None:
    store = EvidenceStore.from_raw_input(RawInput(company_name="Duolingo"))
    evidence = store.add_claim(
        claim="Existing claim",
        source_id="S0",
        locator="test",
        claim_type="assumption",
        confidence="high",
    )
    artifact = {"claim": "Existing claim", "evidence_ids": ["E999"]}

    repaired, result = validate_and_repair_evidence(artifact, store, module_name="lens_fit")

    assert result.ok
    assert repaired["evidence_ids"] == [evidence.id]
    assert "lens_fit" in store.items[evidence.id].used_by_modules
