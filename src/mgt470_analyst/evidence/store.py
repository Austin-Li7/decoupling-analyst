from dataclasses import dataclass, field

from mgt470_analyst.schemas.evidence import EvidenceItem, EvidenceStoreArtifact
from mgt470_analyst.schemas.raw_input import RawInput


@dataclass
class EvidenceStore:
    items: dict[str, EvidenceItem] = field(default_factory=dict)
    _next_id: int = 1

    @classmethod
    def from_raw_input(cls, raw_input: RawInput) -> "EvidenceStore":
        store = cls()
        store.add_claim(
            claim=f"{raw_input.company_name} was provided as the target company by the user.",
            source_id="S0",
            locator="CLI input",
            claim_type="assumption",
            confidence="high",
        )
        if raw_input.ticker:
            store.add_claim(
                claim=f"{raw_input.company_name} has ticker {raw_input.ticker} in the user input.",
                source_id="S0",
                locator="CLI input",
                claim_type="assumption",
                confidence="high",
            )
        if raw_input.website:
            store.add_claim(
                claim=f"{raw_input.company_name} website was supplied as {raw_input.website}.",
                source_id="S1",
                locator="CLI input --url",
                claim_type="assumption",
                confidence="medium",
            )
        return store

    def add_claim(
        self,
        claim: str,
        source_id: str,
        locator: str,
        claim_type: str,
        confidence: str,
        used_by_modules: list[str] | None = None,
    ) -> EvidenceItem:
        evidence_id = f"E{self._next_id}"
        self._next_id += 1
        item = EvidenceItem(
            id=evidence_id,
            claim=claim,
            source_id=source_id,
            locator=locator,
            claim_type=claim_type,  # type: ignore[arg-type]
            confidence=confidence,  # type: ignore[arg-type]
            used_by_modules=used_by_modules or [],
        )
        self.items[evidence_id] = item
        return item

    def mark_used(self, evidence_id: str, module_name: str) -> None:
        item = self.items[evidence_id]
        if module_name not in item.used_by_modules:
            item.used_by_modules.append(module_name)

    def to_artifact(self) -> EvidenceStoreArtifact:
        return EvidenceStoreArtifact(self.items)
