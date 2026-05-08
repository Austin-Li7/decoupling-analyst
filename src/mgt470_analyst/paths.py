import re
from datetime import datetime
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "company"


def build_run_id(company_name: str, created_at: datetime | None = None) -> str:
    stamp = (created_at or datetime.now().astimezone()).strftime("%Y%m%d-%H%M%S")
    return f"{slugify(company_name)}-{stamp}"


def ensure_run_dir(runs_dir: Path, company_name: str) -> tuple[str, Path]:
    run_id = build_run_id(company_name)
    run_dir = runs_dir / run_id
    counter = 2
    while run_dir.exists():
        run_dir = runs_dir / f"{run_id}-{counter}"
        counter += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir.name, run_dir
