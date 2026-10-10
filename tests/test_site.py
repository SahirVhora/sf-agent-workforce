"""SEO and integrity tests for the GitHub Pages site.

These run in CI so that metadata, links and advertised numbers cannot drift.
"""

import json
import re
import struct
import subprocess
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from agent_workforce.checks import CHECKS

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "https://sahirvhora.github.io/sf-agent-workforce/"
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.ids: list[str] = []
        self.canonical = None
        self.h1 = 0
        self.lang = None
        self.title = ""
        self.summaries: list[str] = []
        self.jsonld: list[str] = []
        self.imgs_without_alt = 0
        self._in = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        for attr in ("href", "src"):
            if a.get(attr):
                self.links.append(a[attr])
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "img" and not a.get("alt"):
            self.imgs_without_alt += 1
        if tag == "title":
            self._in = "title"
        if tag == "summary":
            self._in = "summary"
            self.summaries.append("")
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in = "jsonld"
            self.jsonld.append("")

    def handle_endtag(self, tag):
        if tag in ("title", "summary", "script"):
            self._in = None

    def handle_data(self, data):
        if self._in == "title":
            self.title += data
        elif self._in == "summary":
            self.summaries[-1] += data
        elif self._in == "jsonld":
            self.jsonld[-1] += data


@pytest.fixture(scope="module")
def page():
    p = Page()
    p.feed(INDEX)
    return p


@pytest.fixture(scope="module")
def dist():
    out = subprocess.run(
        ["bash", str(ROOT / "scripts" / "build_pages_artifact.sh")], capture_output=True, text=True, check=False
    )
    assert out.returncode == 0, out.stderr
    return ROOT / "dist"


def test_title_and_description_lengths(page):
    assert 30 <= len(page.title) <= 60, page.title
    assert 70 <= len(page.meta["description"]) <= 160, len(page.meta["description"])


def test_lang_single_h1_unique_ids_alt_text(page):
    assert page.lang and page.lang.startswith("en")
    assert page.h1 == 1
    assert len(page.ids) == len(set(page.ids))
    assert page.imgs_without_alt == 0


def test_canonical_urls_agree(page):
    assert page.canonical == CANONICAL
    assert page.meta["og:url"] == CANONICAL
    assert page.meta["twitter:url"] == CANONICAL
    assert page.meta["robots"].startswith("index, follow")


def test_social_image_is_1200x630_png(page):
    for key in ("og:image", "twitter:image"):
        assert page.meta[key] == CANONICAL + "preview.png"
    data = (ROOT / "preview.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (1200, 630)
    assert page.meta["og:image:width"] == "1200" and page.meta["og:image:height"] == "630"
    assert page.meta["twitter:card"] == "summary_large_image"


def test_structured_data_valid_and_matches_visible_faq(page):
    assert len(page.jsonld) == 1
    graph = json.loads(page.jsonld[0])["@graph"]
    types = {node["@type"] for node in graph}
    assert {"SoftwareSourceCode", "Person", "FAQPage"} <= types
    software = next(n for n in graph if n["@type"] == "SoftwareSourceCode")
    assert software["url"] == CANONICAL
    assert software["codeRepository"] == "https://github.com/SahirVhora/sf-agent-workforce"
    faq = next(n for n in graph if n["@type"] == "FAQPage")
    # Google requires FAQ structured data to match content visible on the page.
    assert [q["name"] for q in faq["mainEntity"]] == [s.strip() for s in page.summaries]


def test_robots_and_sitemap():
    robots = (ROOT / "robots.txt").read_text()
    assert f"Sitemap: {CANONICAL}sitemap.xml" in robots
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in ET.parse(ROOT / "sitemap.xml").getroot().findall("s:url/s:loc", ns)]
    assert locs == [CANONICAL]


def test_local_links_resolve_in_published_site(page, dist):
    missing = []
    for raw in page.links:
        parts = urlsplit(raw)
        if parts.scheme or parts.netloc or raw.startswith(("#", "mailto:")):
            continue
        if not (dist / parts.path).exists():
            missing.append(raw)
    assert not missing, missing


def test_published_site_contents(dist):
    for name in (
        "index.html",
        "preview.png",
        "favicon.svg",
        "robots.txt",
        "sitemap.xml",
        "sample-report.html",
        "downloads/EU_AI_Act_HR_Audit_Checklist.xlsx",
        "schema/agent_register.schema.json",
        ".nojekyll",
    ):
        assert (dist / name).exists(), name
    assert not (dist / "tests").exists() and not (dist / "agent_workforce").exists()


def test_schema_id_is_published_url():
    schema = json.loads((ROOT / "schema" / "agent_register.schema.json").read_text())
    assert schema["$id"] == CANONICAL + "schema/agent_register.schema.json"


def test_advertised_check_count_is_true():
    n = len(CHECKS)
    assert f'<strong class="blue">{n}</strong>' in INDEX
    assert INDEX.count("<tr><td>CHK-AGT-") == n


def test_advertised_test_count_is_true(request):
    n = request.session.testscollected
    assert f'<strong class="green">{n}</strong>' in INDEX, f"index.html should advertise {n} tests"
    assert f"{n} tests" in (ROOT / "README.md").read_text()


@pytest.mark.parametrize("rel", ["index.html", "README.md", "docs/DATA_MODEL.md", "docs/CHECKS.md"])
def test_house_style_no_em_dashes(rel):
    assert "—" not in (ROOT / rel).read_text(encoding="utf-8")


def test_external_links_use_https(page):
    insecure = [u for u in page.links if u.startswith("http://")]
    assert not insecure, insecure


def test_keywords_appear_in_visible_copy():
    body = re.sub(r"<[^>]+>", " ", INDEX.split("<body>", 1)[1]).lower()
    for phrase in ("successfactors", "eu ai act", "ai agents", "checklist", "annex iii"):
        assert phrase in body, phrase
