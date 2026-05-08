import re
from pathlib import Path

from pypdf import PdfReader

from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.schemas.deck_claims import DeckClaim, DeckClaims

# Substrings that mark HBS / case-publisher boilerplate. Lines containing any
# of these are skipped — they are never analytically useful.
BOILERPLATE_MARKERS = (
    "hbs cases are developed",
    "harvard business school",
    "for the exclusive use",
    "this document is authorized",
    "copying or posting",
    "purchased this case",
    "do not copy",
    "all rights reserved",
)

# Lines must contain at least one of these signal tokens to be considered a
# claim worth keeping. We're looking for quantitative or business-substantive
# content, not topic sentences.
SIGNAL_TOKENS = (
    "%",
    "$",
    "₹",
    "€",
    "£",
    "million",
    "billion",
    "thousand",
    "ARR",
    "MRR",
    "CAC",
    "CLV",
    "LTV",
    "GMV",
    "DAU",
    "MAU",
    "YoY",
    "QoQ",
    "TAM",
    "SAM",
    "growth",
    "revenue",
    "margin",
    "customer",
    "users",
    "retention",
    "conversion",
    "marketplace",
    "logistics",
    "subscription",
)

MIN_CLAIM_LENGTH = 40
MAX_CLAIM_LENGTH = 400


def extract_deck_claims(files: list[str], store: EvidenceStore) -> list[DeckClaims]:
    artifacts: list[DeckClaims] = []
    for file_index, file_name in enumerate(files, start=1):
        path = Path(file_name)
        # Each file gets its own evidence-store source_id so the audit trail
        # stays clean.
        source_id = _register_source(store, file_name, file_index)

        seen: set[str] = set()
        claims: list[DeckClaim] = []
        for sentence, page_num in _iter_sentences(path):
            normalized = _normalize(sentence)
            if not _is_useful(normalized, seen):
                continue
            seen.add(normalized.lower())
            evidence = store.add_claim(
                claim=normalized,
                source_id=source_id,
                locator=f"{path.name} p.{page_num}" if page_num else path.name,
                claim_type="management_claim",
                confidence="medium",
            )
            claims.append(
                DeckClaim(
                    id=f"DC{len(claims) + 1}",
                    claim=normalized,
                    claim_type=_classify(normalized),
                    page=page_num,
                    verbatim=normalized,
                    evidence_id=evidence.id,
                )
            )
        artifacts.append(DeckClaims(source_file=file_name, claims=claims))
    return artifacts


def _register_source(store: EvidenceStore, file_name: str, file_index: int) -> str:
    """Add a synthetic source entry on the evidence store for this file.

    EvidenceStore today doesn't model sources directly — it just stores
    source_id strings on each item. We mint a deterministic per-file id so
    downstream audit can group claims by origin.
    """
    return f"F{file_index}"


def _iter_sentences(path: Path) -> list[tuple[str, int | None]]:
    if not path.exists():
        return []
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [(s, None) for s in _split_sentences(text)]
    if suffix == ".pdf":
        return _read_pdf_sentences(path)
    return []


def _read_pdf_sentences(path: Path) -> list[tuple[str, int | None]]:
    reader = PdfReader(path)
    out: list[tuple[str, int | None]] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        # PDF extraction often inserts spurious word breaks ("F lipkart"). Heal
        # the most common ones before splitting into sentences.
        text = re.sub(r"\b([A-Za-z])\s+([a-z]{3,})\b", r"\1\2", text)
        for sentence in _split_sentences(text):
            out.append((sentence, page_index))
    return out


def _split_sentences(text: str) -> list[str]:
    # Crude but adequate: split on sentence terminators, keeping the punctuation.
    # We then filter aggressively in `_is_useful`.
    cleaned = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"])", cleaned)
    return [p.strip() for p in parts if p.strip()]


def _normalize(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence).strip()


def _is_useful(sentence: str, seen: set[str]) -> bool:
    if len(sentence) < MIN_CLAIM_LENGTH or len(sentence) > MAX_CLAIM_LENGTH:
        return False
    lower = sentence.lower()
    if lower in seen:
        return False
    if any(marker in lower for marker in BOILERPLATE_MARKERS):
        return False
    # Reject lines that are mostly numbers or punctuation (table fragments).
    alpha_chars = sum(1 for ch in sentence if ch.isalpha())
    if alpha_chars < len(sentence) * 0.5:
        return False
    if not any(token.lower() in lower for token in SIGNAL_TOKENS):
        return False
    return True


def _classify(sentence: str) -> str:
    lower = sentence.lower()
    if "tam" in lower or "market size" in lower:
        return "tam"
    if any(ch in sentence for ch in "%$₹€£") or re.search(r"\d", sentence):
        return "metric"
    if "will" in lower or "expects" in lower or "forecast" in lower:
        return "forecast"
    return "qualitative"
