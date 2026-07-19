"""Typer CLI — entry point ``civic``.

Commands orchestrate the store and exporters. Adapters/ingest and source seeding are
Phase 2 concerns; ``ingest`` is intentionally a stub until adapters land.
"""
from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import List, Optional

import typer

from . import __version__
from .config import get_settings
from .db import get_connection
from .exports.csv_export import export_csv
from .exports.ics_export import export_ics
from .exports.json_export import export_json
from .intake import IntakeError, ingest_intake
from .store import (
    approve_change,
    pending_reviews,
    reject_change,
    verify,
)

app = typer.Typer(
    add_completion=False,
    help="civic-calendar-engine: curation-first off-cycle election calendar pipeline.",
)
sources_app = typer.Typer(help="Manage the sources registry.")
app.add_typer(sources_app, name="sources")
site_app = typer.Typer(help="Build the static consumer directory site.")
app.add_typer(site_app, name="site")


def _actor(by: Optional[str]) -> str:
    return by or os.environ.get("USER") or "unknown"


def _today_version() -> str:
    return datetime.date.today().strftime("%Y.%m.%d")


def _now_iso_z() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@app.command()
def init() -> None:
    """Create the database from schema.sql (idempotent)."""
    settings = get_settings()
    with get_connection() as conn:
        conn.execute("SELECT 1")
    typer.echo(f"Initialized database at {settings.db_path}")


@app.command()
def intake(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    by: Optional[str] = typer.Option(None, "--by", help="Actor name for audit."),
) -> None:
    """Validate and upsert a YAML intake file (all-or-nothing)."""
    actor = _actor(by)
    try:
        with get_connection() as conn:
            results = ingest_intake(conn, file, actor)
    except IntakeError as exc:
        typer.secho("Intake rejected — no records were written:", fg=typer.colors.RED)
        for err in exc.errors:
            typer.echo(f"  {err}")
        raise typer.Exit(code=1)

    summary: dict[str, int] = {}
    for r in results:
        summary[r.action] = summary.get(r.action, 0) + 1
    typer.secho(f"Ingested {len(results)} record(s): ", fg=typer.colors.GREEN, nl=False)
    typer.echo(", ".join(f"{k}={v}" for k, v in sorted(summary.items())))


@app.command()
def ingest(
    state: Optional[str] = typer.Option(None, "--state", help="Run one state's adapters."),
    all_states: bool = typer.Option(False, "--all", help="Run all registered adapters."),
) -> None:
    """Run registered state adapters (Phase 2 — not yet implemented)."""
    typer.secho(
        "`civic ingest` is a Phase 2 feature (adapters). Use `civic intake` for "
        "manual YAML curation in Phase 1.",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(code=2)


@app.command()
def review() -> None:
    """List elections in needs_review together with their pending changes."""
    with get_connection() as conn:
        items = pending_reviews(conn)
    if not items:
        typer.echo("No elections pending review.")
        return
    for item in items:
        e = item["election"]
        typer.secho(
            f"\n{e['id']}  {e['state']}  {e['jurisdiction_name']} — "
            f"{e['election_type']} ({e['election_date']})",
            fg=typer.colors.CYAN,
        )
        for c in item["changes"]:
            typer.echo(
                f"  change {c['id']}: {c['field']}: "
                f"{c['old_value']!r} → {c['new_value']!r}"
            )
    typer.echo("\nApprove with `civic approve <id>...`, reject with `civic reject <id>...`.")


@app.command()
def approve(
    change_ids: List[int] = typer.Argument(..., help="Pending change id(s) to apply."),
    by: Optional[str] = typer.Option(None, "--by"),
) -> None:
    """Apply pending change(s)."""
    actor = _actor(by)
    with get_connection() as conn:
        for cid in change_ids:
            try:
                approve_change(conn, cid, actor)
                typer.secho(f"Applied change {cid}.", fg=typer.colors.GREEN)
            except ValueError as exc:
                typer.secho(f"Change {cid}: {exc}", fg=typer.colors.RED)
                raise typer.Exit(code=1)


@app.command()
def reject(
    change_ids: List[int] = typer.Argument(..., help="Pending change id(s) to discard."),
    by: Optional[str] = typer.Option(None, "--by"),
) -> None:
    """Discard pending change(s); stored values are left untouched."""
    actor = _actor(by)
    with get_connection() as conn:
        for cid in change_ids:
            try:
                reject_change(conn, cid, actor)
                typer.secho(f"Rejected change {cid}.", fg=typer.colors.GREEN)
            except ValueError as exc:
                typer.secho(f"Change {cid}: {exc}", fg=typer.colors.RED)
                raise typer.Exit(code=1)


@app.command(name="verify")
def verify_cmd(
    election_id: str = typer.Argument(..., help="Election id to mark verified."),
    by: str = typer.Option(..., "--by", help="Verifier name."),
) -> None:
    """Mark an election verified."""
    with get_connection() as conn:
        ok = verify(conn, election_id, by)
    if not ok:
        typer.secho(f"No such election: {election_id}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.secho(f"Verified {election_id} (by {by}).", fg=typer.colors.GREEN)


@app.command()
def export(
    kinds: List[str] = typer.Argument(..., help="One or more of: json csv ics"),
    version: Optional[str] = typer.Option(None, "--version", help="YYYY.MM.DD"),
    out: Optional[str] = typer.Option(None, "--out", help="Output directory."),
    include_unverified: bool = typer.Option(
        False, "--include-unverified", help="Include staging (unverified) records."
    ),
    since: Optional[str] = typer.Option(None, "--since", help="Changelog floor date (CSV)."),
) -> None:
    """Produce json/csv/ics exports."""
    settings = get_settings()
    version = version or _today_version()
    out_dir = out or settings.export_dir
    generated_at = _now_iso_z()
    generated_at_dt = datetime.datetime.now(datetime.timezone.utc)

    valid = {"json", "csv", "ics"}
    unknown = [k for k in kinds if k not in valid]
    if unknown:
        typer.secho(f"Unknown export kind(s): {', '.join(unknown)}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    with get_connection() as conn:
        for kind in kinds:
            if kind == "json":
                manifest = export_json(
                    conn, out_dir, version, generated_at, include_unverified
                )
            elif kind == "csv":
                manifest = export_csv(
                    conn, out_dir, version, generated_at, include_unverified, since
                )
            else:  # ics
                manifest = export_ics(
                    conn,
                    out_dir,
                    version,
                    generated_at,
                    generated_at_dt,
                    settings.ics_domain,
                    include_unverified,
                )
            typer.secho(
                f"{kind}: wrote {len(manifest)} file(s) (version {version}).",
                fg=typer.colors.GREEN,
            )


@sources_app.command("seed")
def sources_seed(
    file: Path = typer.Option(
        Path("seed/sources.yaml"), "--file", exists=True, dir_okay=False, readable=True
    ),
) -> None:
    """Load seed/sources.yaml into the sources table (idempotent by URL)."""
    import yaml

    entries = yaml.safe_load(file.read_text(encoding="utf-8")) or []
    inserted = 0
    with get_connection() as conn:
        for entry in entries:
            conn.execute(
                """
                INSERT INTO sources (state, name, url, adapter, check_frequency_days, enabled)
                VALUES (:state, :name, :url, :adapter, :check_frequency_days, :enabled)
                ON CONFLICT(url) DO UPDATE SET
                    state = excluded.state,
                    name = excluded.name,
                    adapter = excluded.adapter,
                    check_frequency_days = excluded.check_frequency_days,
                    enabled = excluded.enabled
                """,
                {
                    "state": entry["state"],
                    "name": entry["name"],
                    "url": entry["url"],
                    "adapter": entry.get("adapter"),
                    "check_frequency_days": entry.get("check_frequency_days", 14),
                    "enabled": 1 if entry.get("enabled", True) else 0,
                },
            )
            inserted += 1
    typer.secho(f"Seeded {inserted} source(s).", fg=typer.colors.GREEN)


@site_app.command("build")
def site_build(
    version: Optional[str] = typer.Option(None, "--version", help="YYYY.MM.DD"),
    out: Optional[str] = typer.Option(None, "--out", help="Output directory."),
    origin: Optional[str] = typer.Option(None, "--origin", help="Deploy origin, e.g. https://host"),
    base_path: Optional[str] = typer.Option(
        None, "--base-path", help="Subpath prefix for project-page hosting, e.g. /Midterm-Hub"
    ),
    include_unverified: bool = typer.Option(
        False, "--include-unverified", help="Include staging (unverified) records."
    ),
    no_downloads: bool = typer.Option(
        False, "--no-downloads", help="Skip generating the /downloads/ JSON/CSV/ICS files."
    ),
    demo: bool = typer.Option(
        False, "--demo", help="Render a site-wide banner marking the data as illustrative."
    ),
) -> None:
    """Generate the complete static website from verified records."""
    from .site.build import build_site

    settings = get_settings()
    version = version or _today_version()
    out_dir = out or (settings.export_dir.rstrip("/") + "/site")
    origin = origin if origin is not None else settings.site_origin
    base_path = base_path if base_path is not None else settings.site_base_path

    with get_connection() as conn:
        result = build_site(
            conn, out_dir, origin=origin, base_path=base_path, version=version,
            include_unverified=include_unverified, with_downloads=not no_downloads,
            demo=demo,
        )
    typer.secho(
        f"Built {result.pages_written} page(s) into {result.out_dir} "
        f"(version {result.version}).",
        fg=typer.colors.GREEN,
    )
    if result.downloads_written:
        typer.echo("Wrote downloadable JSON/CSV/ICS under /downloads/.")


@app.command()
def stats() -> None:
    """Show counts by state/status/type and the pending-review count."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM elections").fetchone()[0]
        by_status = conn.execute(
            "SELECT status, COUNT(*) c FROM elections GROUP BY status ORDER BY status"
        ).fetchall()
        by_state = conn.execute(
            "SELECT state, COUNT(*) c FROM elections GROUP BY state ORDER BY state"
        ).fetchall()
        by_type = conn.execute(
            "SELECT election_type, COUNT(*) c FROM elections GROUP BY election_type "
            "ORDER BY election_type"
        ).fetchall()
        pending = conn.execute(
            "SELECT COUNT(*) FROM changes WHERE applied = 0"
        ).fetchone()[0]

    typer.secho(f"Total elections: {total}", fg=typer.colors.CYAN)
    typer.echo("By status: " + ", ".join(f"{r['status']}={r['c']}" for r in by_status))
    typer.echo("By state:  " + ", ".join(f"{r['state']}={r['c']}" for r in by_state))
    typer.echo("By type:   " + ", ".join(f"{r['election_type']}={r['c']}" for r in by_type))
    typer.secho(f"Pending review changes: {pending}", fg=typer.colors.YELLOW)


@app.command()
def version() -> None:
    """Print the engine version."""
    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
