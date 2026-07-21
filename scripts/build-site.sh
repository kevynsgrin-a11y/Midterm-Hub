#!/usr/bin/env bash
# Production static-site build for midtermwatch.com.
# One command any static host can run (Cloudflare Pages / Netlify / GitHub Actions):
#   Build command:  bash scripts/build-site.sh dist
#   Output dir:     dist   (first arg; defaults to "dist")
#
# Cloudflare Pages: set the build command above, output dir "dist", and a
# PYTHON_VERSION build variable (e.g. 3.11). No other configuration needed.
set -euo pipefail

OUT="${1:-dist}"
ORIGIN="${SITE_ORIGIN:-https://midtermwatch.com}"
CNAME_HOST="${SITE_CNAME:-midtermwatch.com}"

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

export CIVIC_DB_PATH="build.db"
rm -f build.db build.db-wal build.db-shm

civic init
# Real curated dataset: every YAML under intake/ is validated all-or-nothing and
# upserted. Records were human-reviewed against official sources before commit,
# so the build marks them verified (actor "editorial").
for f in intake/*.yaml; do
  civic intake "$f" --by editorial
done
python - <<'PY'
import sqlite3
from civic.store import verify
conn = sqlite3.connect("build.db")
conn.row_factory = sqlite3.Row
for row in conn.execute("SELECT id FROM elections"):
    verify(conn, row["id"], "editorial")
conn.commit()
PY

civic site build \
  --origin "$ORIGIN" \
  --base-path "" \
  --cname "$CNAME_HOST" \
  --out "$OUT"

echo "Built site into '$OUT' for $ORIGIN (CNAME $CNAME_HOST)"
