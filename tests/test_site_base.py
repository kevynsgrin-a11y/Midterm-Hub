"""URL, escaping, and attribute helpers in civic.site.base.

These are the lowest-level pure functions in the renderer, so a silent bug here
reaches every page. Coverage targets the normalization rules, the two deploy
shapes (domain root vs project subpath), and the href allowlist that defuses a
poisoned ``source_url``.
"""
from __future__ import annotations

import pytest

from civic.site.base import SiteConfig, absu, asset, attrs, esc, rel, safe_href

ROOT = SiteConfig(origin="https://example.test")
SUB = SiteConfig(origin="https://example.test", base_path="/Midterm-Hub")


class TestEsc:
    def test_escapes_markup_and_quotes(self):
        assert esc("a<b>&c") == "a&lt;b&gt;&amp;c"
        # quote=True: single and double quotes must not break out of an attribute.
        assert esc('say "hi" & \'bye\'') == "say &quot;hi&quot; &amp; &#x27;bye&#x27;"

    def test_none_and_non_string(self):
        assert esc(None) == ""
        assert esc(0) == "0"
        assert esc(True) == "True"
        assert esc("2027-05-04") == "2027-05-04"

    def test_plain_text_untouched(self):
        assert esc("Town of Example") == "Town of Example"


class TestSiteConfigNormalization:
    def test_origin_trailing_slash_stripped(self):
        assert SiteConfig(origin="https://x.github.io/").origin == "https://x.github.io"

    def test_base_path_gains_leading_slash_and_loses_trailing(self):
        assert SiteConfig(base_path="Midterm-Hub/").base_path == "/Midterm-Hub"
        assert SiteConfig(base_path=" /Midterm-Hub ").base_path == "/Midterm-Hub"

    def test_root_base_path_collapses_to_empty(self):
        assert SiteConfig(base_path="/").base_path == ""
        assert SiteConfig(base_path="").base_path == ""

    def test_defaults(self):
        cfg = SiteConfig()
        assert cfg.origin == "https://plumbline.example"
        assert cfg.base_path == ""
        assert cfg.asset_map == {}
        assert cfg.critical_css == ""


class TestRel:
    def test_root_deploy(self):
        assert rel(ROOT, "/about/") == "/about/"
        assert rel(ROOT, "about/") == "/about/"
        assert rel(ROOT, "/") == "/"

    def test_subpath_deploy_prefixes_every_internal_link(self):
        assert rel(SUB, "/about/") == "/Midterm-Hub/about/"
        assert rel(SUB, "about/") == "/Midterm-Hub/about/"

    def test_external_anchor_and_mailto_pass_through_unprefixed(self):
        for p in (
            "https://sos.example.gov/va",
            "http://example.test",
            "mailto:info@example.test",
            "#main",
        ):
            assert rel(SUB, p) == p


class TestAbsu:
    def test_builds_absolute_from_parts(self):
        assert absu(ROOT, "/states/VA/") == "https://example.test/states/VA/"
        assert absu(ROOT, "states/VA/") == "https://example.test/states/VA/"

    def test_subpath_deploy(self):
        assert absu(SUB, "/states/VA/") == (
            "https://example.test/Midterm-Hub/states/VA/"
        )

    def test_already_absolute_passes_through(self):
        assert absu(SUB, "https://cdn.example/x.png") == "https://cdn.example/x.png"


class TestAsset:
    # Callers pass a bare name (see render.py: asset(cfg, "styles.css")); asset()
    # is what prepends /assets/.
    def test_content_hashed_filename_is_used_when_supplied(self):
        cfg = SiteConfig(asset_map={"styles.css": "styles.abc123.css"})
        assert asset(cfg, "styles.css") == "/assets/styles.abc123.css"

    def test_leading_slash_is_optional(self):
        cfg = SiteConfig(asset_map={"app.js": "app.def456.js"})
        assert asset(cfg, "/app.js") == "/assets/app.def456.js"

    def test_unmapped_asset_keeps_its_name(self):
        assert asset(ROOT, "site.js") == "/assets/site.js"

    def test_subpath_deploy_prefixes_assets(self):
        cfg = SiteConfig(base_path="/Midterm-Hub", asset_map={"s.css": "s.1.css"})
        assert asset(cfg, "s.css") == "/Midterm-Hub/assets/s.1.css"


class TestSafeHref:
    @pytest.mark.parametrize(
        "url",
        [
            "https://sos.example.gov/va",
            "http://sos.example.gov/va",
            "mailto:info@example.test",
            "/states/VA/",
            "#main",
            "./sibling",
            "../parent",
        ],
    )
    def test_allowed_forms_pass_through(self, url):
        assert safe_href(url) == url

    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "  javascript:alert(1)  ",
            "data:text/html;base64,PHNjcmlwdD4=",
            "vbscript:msgbox(1)",
            "file:///etc/passwd",
        ],
    )
    def test_other_schemes_neutralized(self, url):
        assert safe_href(url) == "#"

    def test_protocol_relative_rejected_before_allowlist(self):
        # "//evil.example/x" starts with "/" and would otherwise pass, silently
        # resolving off-site.
        assert safe_href("//evil.example/x") == "#"
        assert safe_href("  //evil.example/x  ") == "#"

    def test_missing_url(self):
        assert safe_href(None) == "#"

    def test_surrounding_whitespace_stripped(self):
        assert safe_href("  https://sos.example.gov/va  ") == "https://sos.example.gov/va"


class TestAttrs:
    def test_true_renders_bare_none_and_false_are_skipped(self):
        assert attrs(id="x", hidden=True, disabled=False, title=None) == (
            ' id="x" hidden'
        )

    def test_trailing_underscore_stripped_and_inner_underscores_hyphenated(self):
        assert attrs(class_="card", data_testid="row") == (
            ' class="card" data-testid="row"'
        )

    def test_values_are_escaped(self):
        assert attrs(title='He said "no" & <left>') == (
            " title=\"He said &quot;no&quot; &amp; &lt;left&gt;\""
        )

    def test_empty_string_value_still_renders_the_attribute(self):
        # Only None/False are dropped — "" is a real (empty) value.
        assert attrs(data_empty="", alt=None) == ' data-empty=""'

    def test_insertion_order_preserved(self):
        assert attrs(b="2", a="1", c="3") == ' b="2" a="1" c="3"'

    def test_empty_when_nothing_renderable(self):
        assert attrs() == ""
        assert attrs(a=None, b=False) == ""
