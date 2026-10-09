"""Create a stable, build-time frontend payload from curated intake records.

The intake files remain the source of truth. Records are validated by the same
Pydantic model used by the audited pipeline before serialization. The open-data
downloads (JSON, CSV, ICS) and their manifest are derived from the same payload.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from civic.downloads import write_downloads
from civic.frontend_data import build_payload, build_records

OUT = ROOT / "generated" / "elections.json"
DOWNLOADS = ROOT / "public" / "downloads"
MANIFEST = ROOT / "generated" / "downloads-manifest.json"


def main() -> None:
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    records = build_records(ROOT / "intake", previous)
    payload, changed = build_payload(records, previous)
    if changed:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(records)} elections to {OUT.relative_to(ROOT)}")
    else:
        print(f"Validated {len(records)} unchanged elections; retained generated_at")
    manifest = write_downloads(payload, DOWNLOADS, MANIFEST)
    print(f"Wrote {len(manifest['files'])} downloads to {DOWNLOADS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
