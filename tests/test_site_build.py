"""Static site generator: file emission, SEO, escaping, hermeticity, base-path,
verified-only filtering, downloads, and edge cases."""
from __future__ import annotations

import datetime
import json
import re
import xml.dom.minidom as minidom
from pathlib import Path

from icalendar import Calendar

from civic.site.build import build_site
from civic.store import upsert, verify

TODAY = datetime.date(2027, 1, 1)
ORIGIN = "https://plumbline.example"


def _seed(conn, make_record, verify_all=True):
    a = upsert(conn, make_record(jurisdiction_name="Town of Example",
                                 election_date="2027-05-04",
                                 registration_deadline="2027-04-12",
                                 early_voting_start="2027-04-16",
                                 early_voting_end="2027-05-01"), actor="t")
    b = upsert(conn, make_record(jurisdiction_name="Borough of Placeholder", state="NJ",
                                 election_date="2027-11-02"), actor="t")
    if verify_all:
        verify(conn, a.election_id, "curator")
        verify(conn, b.election_id, "curator")
    return a.election_id, b.election_id


def _build(conn, tmp_path, **kw):
    return build_site(
        conn, str(tmp_path), origin=ORIGIN, version="2027.01.01",
        generated_at="2027-01-01T00:00:00Z", today=TODAY, **kw,
    )


class TestFileEmission:
    def test_core_pages_written(self, conn, make_record, tmp_path):
        eid, _ = _seed(conn, make_record)
        _build(conn, tmp_path)
        for rel in (
            "index.html", "states/index.html", "about/index.html",
            "methodology/index.html", "data/index.html", "404.html",
            "sitemap.xml", "robots.txt", "assets/styles.css", "assets/site.js",
            "assets/favicon.svg", "states/VA/index.html",
            "elections/VA/town-of-example/index.html",
            f"elections/VA/town-of-example/{eid}/index.html",
        ):
            assert (tmp_path / rel).exists(), rel


class TestSeo:
    def test_canonical_and_jsonld(self, conn, make_record, tmp_path):
        eid, _ = _seed(conn, make_record)
        _build(conn, tmp_path)
        html = (tmp_path / f"elections/VA/town-of-example/{eid}/index.html").read_text()
        assert f'<link rel="canonical" href="{ORIGIN}/elections/VA/town-of-example/{eid}/">' in html
        # Every JSON-LD block parses, and an Event with a date-only startDate exists.
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        assert blocks
        graphs = [json.loads(b.replace("<\\/", "</")) for b in blocks]
        event = None
        for g in graphs:
            for node in g.get("@graph", [g]):
                if node.get("@type") == "Event":
                    event = node
        assert event is not None
        assert event["startDate"] == "2027-05-04"  # date-only, no fabricated time
        assert "organizer" not in event and "offers" not in event

    def test_404_noindex_no_canonical(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        _build(conn, tmp_path)
        html = (tmp_path / "404.html").read_text()
        assert 'content="noindex,follow"' in html
        assert "rel=\"canonical\"" not in html

    def test_sitemap_valid(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        _build(conn, tmp_path)
        xml = (tmp_path / "sitemap.xml").read_text()
        dom = minidom.parseString(xml)  # raises if malformed
        locs = {n.firstChild.data for n in dom.getElementsByTagName("loc")}
        assert f"{ORIGIN}/" in locs
        assert f"{ORIGIN}/states/VA/" in locs
        # 404 and downloads are excluded.
        assert not any("404" in l for l in locs)
        assert not any("/downloads/" in l for l in locs)

    def test_robots_has_sitemap(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        _build(conn, tmp_path)
        robots = (tmp_path / "robots.txt").read_text()
        assert f"Sitemap: {ORIGIN}/sitemap.xml" in robots


class TestHermeticAndEscaping:
    def test_no_external_resources(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        _build(conn, tmp_path)
        pat = re.compile(
            r'<(?:link\b[^>]*\brel="(?:stylesheet|icon|preload|manifest)"[^>]*\bhref|'
            r'script\b[^>]*\bsrc|img\b[^>]*\bsrc)="https?://', re.I)
        for f in tmp_path.rglob("*.html"):
            assert not pat.search(f.read_text()), f

    def test_data_is_escaped(self, conn, make_record, tmp_path):
        r = upsert(conn, make_record(jurisdiction_name="Town <script>x</script>"), actor="t")
        verify(conn, r.election_id, "c")
        _build(conn, tmp_path)
        # The dangerous markup must be escaped everywhere it appears.
        for f in tmp_path.rglob("*.html"):
            assert "<script>x</script>" not in f.read_text()


class TestBasePath:
    def test_prefixes_internal_links(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        _build(conn, tmp_path, base_path="/Midterm-Hub")
        home = (tmp_path / "index.html").read_text()
        assert 'href="/Midterm-Hub/states/"' in home
        assert 'href="/Midterm-Hub/assets/styles.css"' in home
        assert f'<link rel="canonical" href="{ORIGIN}/Midterm-Hub/">' in home


class TestFiltering:
    def test_unverified_excluded(self, conn, make_record, tmp_path):
        _seed(conn, make_record, verify_all=False)  # nothing verified
        res = _build(conn, tmp_path)
        # Static pages still render; no state/jurisdiction/election pages.
        assert not (tmp_path / "states/VA").exists()
        home = (tmp_path / "index.html").read_text()
        assert "No upcoming elections" in home


class TestDownloads:
    def test_downloads_generated(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        _build(conn, tmp_path)
        csv = tmp_path / "downloads/csv/2027.01.01/off_cycle_elections_2027.01.01.csv"
        assert csv.exists()
        ics = tmp_path / "downloads/ics/VA/town-of-example.ics"
        assert ics.exists()
        Calendar.from_ical(ics.read_bytes())  # round-trips
        assert (tmp_path / "downloads/json/VA/index.json").exists()

    def test_no_downloads_flag(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        _build(conn, tmp_path, with_downloads=False)
        assert not (tmp_path / "downloads").exists()


class TestQaHardening:
    def test_demo_banner_rendered(self, conn, make_record, tmp_path):
        r = upsert(conn, make_record(), actor="t")
        verify(conn, r.election_id, "c")
        _build(conn, tmp_path, demo=True)
        assert 'class="demo-banner"' in (tmp_path / "index.html").read_text()
        assert (tmp_path / "downloads/NOTICE.txt").exists()

    def test_no_demo_banner_by_default(self, conn, make_record, tmp_path):
        r = upsert(conn, make_record(), actor="t")
        verify(conn, r.election_id, "c")
        _build(conn, tmp_path)
        assert "demo-banner" not in (tmp_path / "index.html").read_text()

    def test_unsafe_source_url_neutralized(self, conn, make_record, tmp_path):
        r = upsert(conn, make_record(source_url="javascript:alert(1)"), actor="t")
        verify(conn, r.election_id, "c")
        _build(conn, tmp_path)
        html = (
            tmp_path / f"elections/VA/town-of-example/{r.election_id}/index.html"
        ).read_text()
        # No clickable javascript: href survives, even though the string may appear as text.
        assert 'href="javascript:' not in html.lower()

    def test_og_cards_generated_and_referenced(self, conn, make_record, tmp_path):
        r = upsert(conn, make_record(), actor="t")
        verify(conn, r.election_id, "c")
        _build(conn, tmp_path, demo=True)
        from civic.site import ogcards

        if not ogcards.available():  # environment without fonts/Pillow
            return
        assert (tmp_path / "og" / "default.png").exists()
        card = tmp_path / "og" / "VA" / "town-of-example" / f"{r.election_id}.png"
        assert card.exists()
        detail = (
            tmp_path / f"elections/VA/town-of-example/{r.election_id}/index.html"
        ).read_text()
        assert f'og:image" content="{ORIGIN}/og/VA/town-of-example/{r.election_id}.png"' in detail
        assert 'twitter:card" content="summary_large_image"' in detail

    def test_stale_tree_pruned(self, conn, make_record, tmp_path):
        r = upsert(conn, make_record(jurisdiction_name="Town of Example"), actor="t")
        verify(conn, r.election_id, "c")
        _build(conn, tmp_path)
        stale = tmp_path / "elections" / "VA" / "old-town" / "index.html"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale")
        _build(conn, tmp_path)  # rebuild should wipe the orphan
        assert not stale.exists()


class TestEdgeCases:
    def test_empty_db_builds(self, conn, tmp_path):
        res = _build(conn, tmp_path)
        assert res.pages_written >= 6  # static pages still render
        assert (tmp_path / "index.html").exists()
        assert (tmp_path / "sitemap.xml").exists()

    def test_missing_optional_fields(self, conn, make_record, tmp_path):
        # Minimal record: no deadlines, no offices, no timezone.
        r = upsert(conn, make_record(offices=[], registration_deadline=None,
                                     early_voting_start=None, early_voting_end=None,
                                     timezone=None, notes=None), actor="t")
        verify(conn, r.election_id, "c")
        _build(conn, tmp_path)
        html = (tmp_path / f"elections/VA/town-of-example/{r.election_id}/index.html").read_text()
        assert "Town of Example" in html
