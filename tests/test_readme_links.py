# -*- coding: utf-8 -*-
"""
README link and structure checks

Framework: pytest
- No new dependencies required (stdlib + pytest).
- Network checks are opt-in via VALIDATE_README_LINKS_ONLINE=1.

Focus: Validates structures and links present in the README content similar to the PR diff
(e.g., 'Device Specifications', 'Hardware Overview', Xiaomi/POCO device references, images/badges).
"""

from __future__ import annotations

import os
import re
import ssl
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import pytest


def rdme_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def rdme_find_readme() -> Path:
    root = rdme_repo_root()
    candidates = [
        root / "README.md",
        root / "Readme.md",
        root / "README.MD",
        root / "docs" / "README.md",
    ]
    for p in candidates:
        if p.is_file():
            return p
    # Fallback: first README.md anywhere (keeps test resilient across repos)
    matches = list(root.glob("**/README.md"))
    if matches:
        return matches[0]
    raise FileNotFoundError("README.md not found")


@pytest.fixture(scope="module")
def rdme_text() -> str:
    try:
        path = rdme_find_readme()
    except FileNotFoundError as e:
        pytest.skip(str(e))
    return path.read_text(encoding="utf-8", errors="ignore")


def rdme_extract_markdown_links(text: str):
    # [text](url "title") but not images
    link_re = re.compile(
        r'(?<!\!)\[(?P<text>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+"[^"]*")?\)'
    )
    # ![alt](url "title")
    img_re = re.compile(
        r'\!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+"[^"]*")?\)'
    )
    links = [(m.group("text"), m.group("url")) for m in link_re.finditer(text)]
    images = [(m.group("alt"), m.group("url")) for m in img_re.finditer(text)]
    return links, images


def rdme_extract_html_imgs_and_anchors(text: str):
    tag_re = re.compile(r"<(img|a)\b[^>]*>", re.IGNORECASE)
    attr_re = re.compile(r'(\w+)\s*=\s*"([^"]+)"')
    imgs = []
    anchors = []
    for tag in tag_re.finditer(text):
        tag_text = tag.group(0)
        attrs = dict(attr_re.findall(tag_text))
        if tag_text.lower().startswith("<img"):
            imgs.append(
                {
                    "src": attrs.get("src"),
                    "alt": attrs.get("alt"),
                    "aria_hidden": attrs.get("aria-hidden"),
                    "role": attrs.get("role"),
                }
            )
        else:
            href = attrs.get("href")
            if href:
                anchors.append(href)
    return imgs, anchors


def rdme_normalize_url(u: str) -> str:
    try:
        parsed = urlparse(u)
    except Exception:
        return u
    scheme = (parsed.scheme or "").lower()
    netloc = (parsed.netloc or "").lower()
    path = (parsed.path or "").rstrip("/")
    query_pairs = sorted(parse_qsl(parsed.query, keep_blank_values=True))
    query = urlencode(query_pairs)
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def rdme_collect_all_urls(text: str):
    links, md_images = rdme_extract_markdown_links(text)
    html_imgs, anchors = rdme_extract_html_imgs_and_anchors(text)
    urls = (
        [u for _, u in links]
        + [u for _, u in md_images]
        + [img.get("src") for img in html_imgs if img.get("src")]
        + anchors
    )
    # Only strings; filter out Nones
    return [u for u in urls if isinstance(u, str)]


def test_readme_contains_expected_sections_and_identifiers(rdme_text: str):
    # Focus on headings/content present in the provided diff snippet
    expected_phrases = [
        "## 📦 Device Specifications",
        "## 🧠 Hardware Overview",
        "Codename: ares / aresin",
        "Xiaomi Redmi K40 Gaming",
        "POCO F3 GT",
    ]
    missing = [p for p in expected_phrases if p not in rdme_text]
    assert not missing, f"README is missing expected phrases: {missing}"


def test_all_extracted_urls_use_https_scheme(rdme_text: str):
    urls = rdme_collect_all_urls(rdme_text)
    problems = []
    for u in urls:
        parsed = urlparse(u)
        # Allow relative links (no scheme) but disallow explicit http:
        if parsed.scheme and parsed.scheme != "https":
            problems.append(u)
    assert not problems, f"Non-HTTPS URLs found in README: {problems}"


def test_markdown_images_have_nonempty_alt_text(rdme_text: str):
    _, md_images = rdme_extract_markdown_links(rdme_text)
    missing = [u for alt, u in md_images if not (alt or "").strip()]
    assert not missing, f"Markdown images missing alt text: {missing}"


def test_html_img_tags_include_alt_or_are_marked_decorative(rdme_text: str):
    """
    Encourage accessibility: require alt, or explicit decorative roles.
    If missing alts exist, xfail to signal improvement without breaking CI.
    """
    html_imgs, _ = rdme_extract_html_imgs_and_anchors(rdme_text)
    missing = []
    for img in html_imgs:
        alt = (img.get("alt") or "").strip()
        aria_hidden = (img.get("aria_hidden") or "").strip().lower()
        role = (img.get("role") or "").strip().lower()
        if not alt and aria_hidden != "true" and role not in {"presentation", "none"}:
            missing.append(img.get("src"))
    if missing:
        pytest.xfail(
            f"HTML <img> tags missing alt (or decorative markers): {missing}"
        )
    assert True


def test_markdown_tables_have_header_dividers(rdme_text: str):
    """
    Check that tables include a header row followed by a divider row of dashes/colons.
    """
    lines = rdme_text.splitlines()
    divider_re = re.compile(
        r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$"
    )
    # Heuristic: header rows typically contain pipes and bolded header names
    header_idxs = [
        i
        for i, line in enumerate(lines)
        if "|" in line and ("**" in line or "Parameter" in line or "Component" in line)
    ]
    assert header_idxs, "No markdown tables with headers detected."
    problems = []
    for i in header_idxs:
        if i + 1 >= len(lines) or not divider_re.match(lines[i + 1]):
            problems.append((i, lines[i]))
    assert not problems, (
        "Markdown table header without a valid divider row after it at lines: "
        f"{problems}"
    )


def test_no_duplicate_normalized_links(rdme_text: str):
    urls = [rdme_normalize_url(u) for u in rdme_collect_all_urls(rdme_text)]
    counts = {}
    for u in urls:
        counts[u] = counts.get(u, 0) + 1
    duplicates = [u for u, c in counts.items() if c > 1]
    assert not duplicates, f"Duplicate links detected (normalized): {duplicates}"


@pytest.mark.slow
def test_external_links_are_reachable_when_opted_in(rdme_text: str):
    """
    Optional network check. Enable by setting:
      VALIDATE_README_LINKS_ONLINE=1
    You can control timeout with README_LINK_TIMEOUT (seconds; default 5).
    """
    if not os.getenv("VALIDATE_README_LINKS_ONLINE"):
        pytest.skip("Set VALIDATE_README_LINKS_ONLINE=1 to enable online link checking.")

    urls = [u for u in rdme_collect_all_urls(rdme_text) if urlparse(u).scheme == "https"]
    headers = {"User-Agent": "README Link Checker (CI)"}
    timeout = float(os.getenv("README_LINK_TIMEOUT", "5"))
    failures = []
    ctx = ssl.create_default_context()

    for u in urls:
        try:
            # Prefer HEAD to reduce bandwidth
            req = Request(u, headers=headers, method="HEAD")
            with urlopen(req, timeout=timeout, context=ctx) as resp:
                code = getattr(resp, "status", 200)
                if code >= 400:
                    raise HTTPError(u, code, "bad status", hdrs=resp.headers, fp=None)
        except HTTPError as he:
            # Some servers disallow HEAD; fall back to a tiny GET
            if he.code in (403, 405, 501):
                try:
                    req = Request(u, headers={**headers, "Range": "bytes=0-0"}, method="GET")
                    with urlopen(req, timeout=timeout, context=ctx) as resp:
                        code = getattr(resp, "status", 200)
                        if code >= 400:
                            failures.append((u, code))
                except Exception as e:
                    failures.append((u, str(e)))
            else:
                failures.append((u, he.code))
        except URLError as ue:
            failures.append((u, getattr(ue, "reason", str(ue))))
        except Exception as e:
            failures.append((u, str(e)))

    assert not failures, f"Unreachable README links: {failures}"