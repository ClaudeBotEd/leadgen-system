"""Tests voor RawPost dedup-fingerprint.

Bug: dezelfde post met andere query-params (?sort=new vs ?sort=old) of
verschillende trailing slashes kreeg verschillende fingerprints, waardoor
dezelfde lead twee keer door de pipeline ging.
"""
from __future__ import annotations

from consumer import RawPost


def _post(url: str) -> RawPost:
    return RawPost(
        id="abc123", source="reddit",
        url=url, title="t", text="x",
    )


def test_fingerprint_stable_for_identical_url() -> None:
    """Idempotent — twee calls op zelfde URL geven zelfde hash."""
    p1 = _post("https://reddit.com/r/x/comments/abc123")
    p2 = _post("https://reddit.com/r/x/comments/abc123")
    assert p1.fingerprint() == p2.fingerprint()


def test_fingerprint_ignores_query_string() -> None:
    """Query-string is een view-modifier, geen content-identiteit.
    ?sort=new en ?sort=old moeten dezelfde lead zijn."""
    p1 = _post("https://reddit.com/r/x/comments/abc123?sort=new")
    p2 = _post("https://reddit.com/r/x/comments/abc123?sort=old")
    assert p1.fingerprint() == p2.fingerprint()


def test_fingerprint_ignores_tracking_params() -> None:
    """utm_*, fbclid, ref= zijn tracking-noise, niet content."""
    p1 = _post("https://reddit.com/r/x/comments/abc123")
    p2 = _post("https://reddit.com/r/x/comments/abc123?utm_source=mail")
    assert p1.fingerprint() == p2.fingerprint()


def test_fingerprint_ignores_fragment() -> None:
    """URL fragments (#comment-xyz) wijzen naar deel van pagina, niet
    een andere post."""
    p1 = _post("https://reddit.com/r/x/comments/abc123")
    p2 = _post("https://reddit.com/r/x/comments/abc123#comment-789")
    assert p1.fingerprint() == p2.fingerprint()


def test_fingerprint_ignores_trailing_slash() -> None:
    """example.com/x en example.com/x/ verwijzen naar zelfde resource."""
    p1 = _post("https://reddit.com/r/x/comments/abc123")
    p2 = _post("https://reddit.com/r/x/comments/abc123/")
    assert p1.fingerprint() == p2.fingerprint()


def test_fingerprint_ignores_scheme_case() -> None:
    """HTTPS vs https mag geen verschil maken."""
    p1 = _post("https://reddit.com/r/x/comments/abc123")
    p2 = _post("HTTPS://reddit.com/r/x/comments/abc123")
    assert p1.fingerprint() == p2.fingerprint()


def test_fingerprint_differs_for_different_paths() -> None:
    """Verschillende paths = verschillende posts."""
    pa = RawPost(id="same", source="reddit",
                 url="https://reddit.com/a", title="t", text="x")
    pb = RawPost(id="same", source="reddit",
                 url="https://reddit.com/b", title="t", text="x")
    assert pa.fingerprint() != pb.fingerprint()


def test_fingerprint_differs_for_different_source() -> None:
    """Source is deel van de identity — reddit/x vs tweakers/x ≠ zelfde post."""
    p1 = RawPost(id="abc", source="reddit",
                 url="https://example.com/x", title="t", text="x")
    p2 = RawPost(id="abc", source="tweakers",
                 url="https://example.com/x", title="t", text="x")
    assert p1.fingerprint() != p2.fingerprint()
