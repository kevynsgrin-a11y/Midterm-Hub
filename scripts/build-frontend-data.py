"""Create a stable, build-time frontend payload from curated intake records.

The intake files remain the source of truth. Records are validated by the same
Pydantic model used by the audited pipeline before serialization.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import yaml
from civic.models import ElectionRecord
from civic.site.data import STATE_NAMES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "elections.json"


def slug(value: str) -> str:
    return "-".join("".join(c.lower() if c.isalnum() else " " for c in value).split())


def main() -> None:
    records: list[dict] = []
    for path in sorted((ROOT / "intake").glob("*.yaml")):
        for raw in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            record = ElectionRecord(**raw)
            data = record.model_dump(mode="json")
            identity = f"{record.state}|{record.jurisdiction_name}|{record.election_type}|{record.election_date}"
            data["id"] = hashlib.sha256(identity.encode()).hexdigest()[:16]
            data["state_name"] = STATE_NAMES.get(record.state, record.state)
            data["slug"] = slug(record.jurisdiction_name)
            data["verified"] = True
            records.append(data)
    records.sort(key=lambda x: (x["election_date"], x["state"], x["jurisdiction_name"]))
    payload = {
        "edition": "2026 Midterm Cycle",
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "demo": False,
        "elections": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} elections to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
