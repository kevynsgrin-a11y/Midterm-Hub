"""Create a stable, build-time frontend payload from curated intake records.

The intake files remain the source of truth. Records are validated by the same
Pydantic model used by the audited pipeline before serialization.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml
from civic.models import ElectionRecord
from civic.site.data import STATE_NAMES

OUT = ROOT / "generated" / "elections.json"


def slug(value: str) -> str:
    return "-".join("".join(c.lower() if c.isalnum() else " " for c in value).split())


def main() -> None:
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    published = {
        (item["state"], item["jurisdiction_name"], item["election_type"], item["election_date"]):
            {key: value for key, value in item.items() if key in ElectionRecord.model_fields and key != "warnings"}
        for item in previous.get("elections", []) if item.get("verified") is True
    }
    records: list[dict] = []
    for path in sorted((ROOT / "intake").glob("*.yaml")):
        for raw in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            key = (raw.get("state", "").strip().upper(), raw.get("jurisdiction_name"), raw.get("election_type"), str(raw.get("election_date")))
            record = ElectionRecord.model_validate(raw, context={"previously_published": published.get(key)})
            data = record.model_dump(mode="json")
            identity = f"{record.state}|{record.jurisdiction_name}|{record.election_type}|{record.election_date}"
            data["id"] = hashlib.sha256(identity.encode()).hexdigest()[:16]
            data["state_name"] = STATE_NAMES.get(record.state, record.state)
            data["slug"] = slug(record.jurisdiction_name)
            data["verified"] = True
            records.append(data)
    records.sort(key=lambda x: (x["election_date"], x["state"], x["jurisdiction_name"]))
    # Rebuilding the same data does not mean its sources were reviewed today.
    if records == previous.get("elections"):
        print(f"Validated {len(records)} unchanged elections; retained generated_at")
        return
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
