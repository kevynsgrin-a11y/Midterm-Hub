"""Structured data, sitemap, and robots in civic.site.seo.

JSON-LD is a contract with search engines, and the module carries real invariants:
a single URL case for @ids (so entities dedupe), no fabricated poll times, and
required fields on nested Events. These tests pin those invariants directly
against the pure builders rather than through a full build.
"""
from __future__ import annotations

import datetime

from civic.site.base import SiteConfig
from civic.site.data import Deadline, JurisdictionView, SiteData, StateView, fmt_short
from civic.site.seo import (
    breadcrumb_ld,
    collection_ld,
    dataset_ld,
    defined_terms_ld,
    event_ld,
    home_graph,
    org_id,
    robots_txt,
    sitemap_xml,
    website_id,
)

CFG = SiteConfig(origin="https://example.test")
SUB = SiteConfig(origin="https://example.test", base_path="/Midterm-Hub")
TODAY = datetime.date(2026, 7, 26)
ELECTION_DATE = datetime.date(2026, 11, 3)
MON = datetime.date(2026, 10, 5)


def _dl(key, label, date, **kw):
    # fmt_short, not "%-d": the platform-independent helper is the reason the
    # source avoids %-d (unsupported on Windows).
    return Deadline(
        key=key, label=label, date=date, formatted=fmt_short(date), **kw
    )


def _site(make_view, *views):
    elections = list(views)
    juris = [
        JurisdictionView(
            state=e.state, state_name=e.state_name, slug=e.jurisdiction_slug,
            name=e.jurisdiction_name, jurisdiction_type=e.jurisdiction_type,
            jurisdiction_type_label=e.jurisdiction_type_label, elections=[e],
        )
        for e in elections
    ]
    by_code: dict[str, list] = {}
    for j in juris:
        by_code.setdefault(j.state, []).append(j)
    states = [
        StateView(
            code=code, name=js[0].state_name,
            elections=[e for j in js for e in j.elections], jurisdictions=js,
        )
        for code, js in sorted(by_code.items())
    ]
    return SiteData(
        version="2026.07.26", generated_at="2026-07-26T00:00:00Z", today=TODAY,
        elections=elections, states=states, jurisdictions=juris,
    )


def _event(make_view, **kw):
    """The single Event node emitted for an election page."""
    return event_ld(CFG, make_view(**kw))["@graph"][0]


def _block(xml: str, loc: str) -> str:
    """The <url>…</url> block whose <loc> is `loc`."""
    for block in xml.split("  <url>")[1:]:
        if f"<loc>{loc}</loc>" in block:
            return block
    raise AssertionError(f"no sitemap entry for {loc}")


class TestIds:
    def test_single_url_case_per_entity(self):
        # Every @id must be the absolute URL plus a fragment so entities dedupe.
        assert org_id(CFG) == "https://example.test/#org"
        assert website_id(CFG) == "https://example.test/#website"

    def test_subpath_deploy_prefixes_ids(self):
        assert org_id(SUB) == "https://example.test/Midterm-Hub/#org"


class TestHomeGraph:
    def test_shape_and_references(self, make_view):
        site = _site(make_view, make_view())
        graph = home_graph(CFG, site)
        assert graph["@context"] == "https://schema.org"
        types = [n["@type"] for n in graph["@graph"]]
        assert types == ["WebSite", "Organization", "WebPage"]
        website, org, page = graph["@graph"]
        # Dangling @id references are the failure this guards.
        assert page["isPartOf"] == {"@id": website["@id"]}
        assert page["about"] == {"@id": org["@id"]}
        assert website["publisher"] == {"@id": org["@id"]}
        assert page["dateModified"] == site.last_modified


class TestBreadcrumb:
    def test_positions_are_one_based_and_items_absolutized(self):
        node = breadcrumb_ld(
            CFG, [("Home", "/"), ("States", "/states/"), ("Current", None)]
        )
        elements = node["itemListElement"]
        assert [e["position"] for e in elements] == [1, 2, 3]
        assert elements[0]["item"] == "https://example.test/"
        assert elements[1]["item"] == "https://example.test/states/"
        # A trailing crumb (the page itself) has no link target.
        assert "item" not in elements[2]
        assert "name" in elements[2]
        assert "@id" not in node

    def test_path_adds_breadcrumb_id(self):
        node = breadcrumb_ld(CFG, [("Home", "/")], path="/states/VA/")
        assert node["@id"] == "https://example.test/states/VA/#breadcrumb"


class TestEventLd:
    def test_core_node_has_no_fabricated_poll_time(self, make_view):
        node = _event(make_view)
        assert node["@type"] == "Event"
        assert node["@id"].endswith("#event")
        # Date-only start: no invented end time or organizer.
        assert node["startDate"] == "2026-11-03"
        assert "endDate" not in node
        assert "organizer" not in node
        assert node["isAccessibleForFree"] is True
        assert node["isBasedOn"] == "https://elections.example.gov/x"

    def test_description_uses_place_type_date_and_offices(self, make_view):
        node = _event(make_view, offices=["Mayor", "Council"])
        assert node["description"] == (
            "The Town of Example, Virginia municipal election is "
            "Tuesday, November 3, 2026. On the ballot: Mayor, Council."
        )

    def test_additional_property_carries_confidence_and_status(self, make_view):
        props = _event(make_view)["additionalProperty"]
        values = {p["name"]: p["value"] for p in props}
        assert values["Data confidence"] == "Confirmed official"
        assert values["Verification status"] == "verified"
        assert values["Verified by"] == "editorial"
        # Absent provenance is omitted rather than invented.
        assert "Source retrieved" not in values

    def test_optional_properties_appear_only_when_present(self, make_view):
        props = _event(
            make_view, verified_by=None,
            source_retrieved_at="2026-07-01T12:00:00Z",
        )["additionalProperty"]
        values = {p["name"] for p in props}
        assert "Verified by" not in values
        assert "Source retrieved" in values

    def test_about_lists_offices(self, make_view):
        assert _event(make_view, offices=["Mayor"])["about"] == [
            {"@type": "Thing", "name": "Mayor"}
        ]
        assert "about" not in _event(make_view, offices=[])

    def test_image_only_when_og_card_supplied(self, make_view):
        assert "image" not in _event(make_view)
        node = event_ld(
            CFG, make_view(), og_path="/og/elections/aa.png"
        )["@graph"][0]
        assert node["image"] == ["https://example.test/og/elections/aa.png"]

    def test_no_subevents_when_no_deadlines(self, make_view):
        assert "subEvent" not in _event(make_view)


class TestEventSubEvents:
    def test_early_voting_end_is_folded_into_the_window(self, make_view):
        node = _event(
            make_view,
            deadlines=[
                _dl("early_voting_start", "Early voting begins", datetime.date(2026, 10, 19)),
                _dl("early_voting_end", "Early voting ends", datetime.date(2026, 10, 30)),
            ],
        )
        subs = node["subEvent"]
        # A separate "early voting ends" Event would duplicate the window.
        assert [s["name"] for s in subs] == ["Early voting"]
        assert subs[0]["endDate"] == "2026-10-30"
        assert subs[0]["startDate"] == "2026-10-19"

    def test_early_voting_start_without_end_has_no_enddate(self, make_view):
        subs = _event(
            make_view,
            deadlines=[_dl("early_voting_start", "Early voting begins", datetime.date(2026, 10, 19))],
        )["subEvent"]
        assert "endDate" not in subs[0]

    def test_nested_events_carry_fields_google_requires(self, make_view):
        subs = _event(
            make_view,
            deadlines=[_dl("registration_deadline", "Registration deadline", MON)],
        )["subEvent"]
        s = subs[0]
        # Omitting these threw "Missing field 'location'" on every deadline node.
        assert s["location"]["@type"] == "Place"
        assert s["eventStatus"] == "https://schema.org/EventScheduled"
        assert s["eventAttendanceMode"] == "https://schema.org/OfflineEventAttendanceMode"
        assert s["superEvent"] == {"@id": s["url"] + "#event"}

    def test_registration_deadline_date_only_without_a_time(self, make_view):
        subs = _event(
            make_view,
            deadlines=[_dl("registration_deadline", "Registration deadline", MON)],
        )["subEvent"]
        assert subs[0]["startDate"] == "2026-10-05"

    def test_registration_deadline_gets_local_offset_when_time_and_tz_known(self, make_view):
        subs = _event(
            make_view,
            timezone="America/New_York",
            deadlines=[
                _dl("registration_deadline", "Registration deadline", MON, time="17:00")
            ],
        )["subEvent"]
        # A real local deadline, expressed in the jurisdiction's own zone (EDT).
        assert subs[0]["startDate"] == "2026-10-05T17:00:00-04:00"

    def test_unresolvable_timezone_falls_back_to_date_only(self, make_view):
        subs = _event(
            make_view,
            timezone="Not/AZone",
            deadlines=[
                _dl("registration_deadline", "Registration deadline", MON, time="17:00")
            ],
        )["subEvent"]
        assert subs[0]["startDate"] == "2026-10-05"

    def test_time_without_timezone_stays_date_only(self, make_view):
        subs = _event(
            make_view,
            timezone=None,
            deadlines=[
                _dl("registration_deadline", "Registration deadline", MON, time="17:00")
            ],
        )["subEvent"]
        assert subs[0]["startDate"] == "2026-10-05"


class TestEventPlace:
    def _loc(self, make_view, **kw):
        return _event(make_view, **kw)["location"]

    def test_statewide_record_is_an_administrative_area(self, make_view):
        loc = self._loc(
            make_view, jurisdiction_type="state", jurisdiction_name="Virginia",
            state_name="Virginia",
        )
        assert loc["@type"] == "AdministrativeArea"
        assert loc["address"]["addressRegion"] == "VA"
        # No invented locality for a statewide race.
        assert "addressLocality" not in loc["address"]

    def test_municipality_carries_locality(self, make_view):
        loc = self._loc(make_view, jurisdiction_type="municipality")
        assert loc["@type"] == "Place"
        assert loc["address"]["addressLocality"] == "Town of Example"
        assert loc["address"]["addressCountry"] == "US"

    def test_county_has_no_locality(self, make_view):
        loc = self._loc(make_view, jurisdiction_type="county")
        assert loc["@type"] == "Place"
        assert "addressLocality" not in loc["address"]


class TestCollectionLd:
    def test_referenced_entities_are_included(self):
        node = collection_ld(
            CFG, "Virginia", "/states/VA/", [("Town of Example", "/elections/VA/town-of-example/")],
            modified="2026-07-26T00:00:00Z",
        )
        graph = node["@graph"]
        page = graph[0]
        # Without these, isPartOf points at a node defined only on the homepage.
        assert [n["@type"] for n in graph] == ["CollectionPage", "WebSite", "Organization"]
        assert page["isPartOf"] == {"@id": website_id(CFG)}
        assert page["dateModified"] == "2026-07-26T00:00:00Z"
        assert page["mainEntity"]["numberOfItems"] == 1
        assert page["mainEntity"]["itemListElement"][0]["url"] == (
            "https://example.test/elections/VA/town-of-example/"
        )

    def test_date_modified_omitted_when_absent(self):
        page = collection_ld(CFG, "X", "/x/", [])["@graph"][0]
        assert "dateModified" not in page
        assert page["mainEntity"]["numberOfItems"] == 0


class TestDefinedTerms:
    def test_all_three_confidence_levels_present(self):
        node = defined_terms_ld(CFG)
        assert node["@type"] == "DefinedTermSet"
        codes = [t["termCode"] for t in node["hasDefinedTerm"]]
        assert codes == ["official", "secondary", "inferred"]
        assert all(t["name"] and t["description"] for t in node["hasDefinedTerm"])


class TestDatasetLd:
    def test_creator_reference_resolves_in_graph(self, make_view):
        site = _site(make_view, make_view())
        graph = dataset_ld(CFG, site)["@graph"]
        dataset, org = graph
        assert dataset["@type"] == "Dataset"
        assert dataset["version"] == "2026.07.26"
        assert dataset["license"].endswith("/by/4.0/")
        # The Organization node is included so creator/publisher resolve on /data/.
        assert dataset["creator"] == {"@id": org_id(CFG)}
        assert org["@id"] == org_id(CFG)


class TestSitemap:
    def test_static_pages_and_priorities(self, make_view):
        xml = sitemap_xml(CFG, _site(make_view, make_view()))
        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in xml
        for loc, pri in [
            ("https://example.test/", "1.0"),
            ("https://example.test/states/", "0.8"),
            ("https://example.test/data/", "0.8"),
            ("https://example.test/about/", "0.5"),
            ("https://example.test/methodology/", "0.5"),
        ]:
            assert f"<loc>{loc}</loc>" in xml
            assert f"<priority>{pri}</priority>" in xml

    def test_lastmod_truncated_to_date(self, make_view):
        site = _site(make_view, make_view(verified_at="2026-07-20T09:30:00Z"))
        xml = sitemap_xml(CFG, site)
        assert "<lastmod>2026-07-20</lastmod>" in xml
        # A full timestamp is not valid in a W3C lastmod.
        assert "2026-07-20T09:30:00Z" not in xml

    def test_lastmod_falls_back_to_generated_at_when_unverified(self, make_view):
        site = _site(make_view, make_view(verified_at=None))
        assert "<lastmod>2026-07-26</lastmod>" in sitemap_xml(CFG, site)

    def test_upcoming_and_past_elections_get_different_priorities(self, make_view):
        site = _site(
            make_view,
            make_view(verified_at="2026-07-20T00:00:00Z"),
            make_view(
                id="b" * 16, election_date=datetime.date(2026, 6, 1),
                verified_at="2026-07-21T00:00:00Z",
            ),
        )
        xml = sitemap_xml(CFG, site)
        upcoming = _block(
            xml, f"https://example.test/elections/VA/town-of-example/{'a' * 16}/"
        )
        past = _block(
            xml, f"https://example.test/elections/VA/town-of-example/{'b' * 16}/"
        )
        assert "<priority>0.7</priority>" in upcoming
        assert "<priority>0.4</priority>" in past
        # Each page's own lastmod wins over the site-wide fallback.
        assert "<lastmod>2026-07-20</lastmod>" in upcoming
        assert "<lastmod>2026-07-21</lastmod>" in past

    def test_state_jurisdiction_and_election_urls_present(self, make_view):
        site = _site(make_view, make_view(verified_at="2026-07-20T00:00:00Z"))
        xml = sitemap_xml(CFG, site)
        assert "<loc>https://example.test/states/VA/</loc>" in xml
        assert "<loc>https://example.test/elections/VA/town-of-example/</loc>" in xml
        assert (
            f"<loc>https://example.test/elections/VA/town-of-example/{'a' * 16}/</loc>"
            in xml
        )

    def test_subpath_deploy_rewrites_every_loc(self, make_view):
        site = _site(make_view, make_view(verified_at="2026-07-20T00:00:00Z"))
        xml = sitemap_xml(SUB, site)
        assert "<loc>https://example.test/Midterm-Hub/</loc>" in xml
        assert "<loc>https://example.test/states/</loc>" not in xml

    def test_ampersand_in_a_path_is_escaped(self, make_view):
        e = make_view(jurisdiction_slug="a&b", verified_at="2026-07-20T00:00:00Z")
        site = _site(make_view, e)
        site.jurisdictions[0].slug = "a&b"
        xml = sitemap_xml(CFG, site)
        assert "a&amp;b" in xml
        assert "a&b" not in xml


class TestRobots:
    def test_points_at_the_sitemap_and_allows_crawling(self):
        text = robots_txt(CFG)
        assert text.startswith("User-agent: *\nAllow: /\n")
        assert "Sitemap: https://example.test/sitemap.xml" in text

    def test_subpath_deploy_rewrites_the_sitemap_url(self):
        assert "Sitemap: https://example.test/Midterm-Hub/sitemap.xml" in robots_txt(SUB)
