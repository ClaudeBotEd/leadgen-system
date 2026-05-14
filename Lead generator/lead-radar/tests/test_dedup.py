"""Regression-tests voor fuzzy dedup."""
from __future__ import annotations

from pathlib import Path


from consumer.processor.dedup import (
    DEFAULT_THRESHOLD,
    TextSignatureStore,
    jaccard,
    shingles,
)


def test_shingles_empty_text() -> None:
    assert shingles("") == frozenset()
    assert shingles("   ") == frozenset()


def test_shingles_too_short() -> None:
    assert shingles("hallo wereld") == frozenset()
    assert shingles("a b") == frozenset()


def test_shingles_basic() -> None:
    sg = shingles("dit is een test van shingles", k=3)
    assert len(sg) == 4


def test_shingles_normalize_case_punct() -> None:
    a = shingles("Wie kent een goede installateur in Utrecht!!")
    b = shingles("wie kent een goede installateur in utrecht")
    assert a == b


def test_shingles_normalize_accents() -> None:
    a = shingles("wij wonen in de regio Luik in België vlakbij grens")
    b = shingles("wij wonen in de regio Liege in Belgie vlakbij grens")
    assert len(a & b) > 0
    assert jaccard(a, b) > 0.4


def test_jaccard_identical() -> None:
    sg = shingles("zoek installateur warmtepomp in Utrecht graag binnenkort")
    assert jaccard(sg, sg) == 1.0


def test_jaccard_disjoint() -> None:
    a = shingles("zoek installateur warmtepomp in Utrecht graag")
    b = shingles("fiets kapot in Amsterdam zoek monteur dringend")
    assert jaccard(a, b) < 0.3


def test_jaccard_empty_returns_zero() -> None:
    assert jaccard(frozenset(), frozenset()) == 0.0
    assert jaccard(frozenset({1, 2}), frozenset()) == 0.0


def test_store_find_duplicate_high_similarity() -> None:
    store = TextSignatureStore()
    store.add("p1", "Zoek met spoed een installateur in Utrecht voor warmtepomp")
    dup = store.find_duplicate(
        "Zoek met spoed een installateur in Utrecht voor warmtepomp"
    )
    assert dup is not None
    assert dup[0] == "p1"
    assert dup[1] == 1.0


def test_store_no_duplicate_when_below_threshold() -> None:
    store = TextSignatureStore(threshold=0.85)
    store.add("p1", "Zoek installateur warmtepomp in Utrecht binnenkort offerte")
    assert store.find_duplicate(
        "Wie kent goede aannemer voor renovatie keuken Amsterdam"
    ) is None


def test_store_persist_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "sigs.json"
    s1 = TextSignatureStore(path=path)
    ok = s1.add(
        "p1",
        "Zoek met spoed een installateur in Utrecht voor warmtepomp graag offerte",
    )
    assert ok is True
    s1.save()
    assert path.exists()

    s2 = TextSignatureStore(path=path)
    assert len(s2) == 1
    assert s2.has("p1")


def test_store_corrupt_file_starts_empty(tmp_path: Path) -> None:
    path = tmp_path / "sigs.json"
    path.write_text("not valid json", encoding="utf-8")
    s = TextSignatureStore(path=path)
    assert len(s) == 0


def test_default_threshold_constant() -> None:
    assert DEFAULT_THRESHOLD == 0.70


def test_store_add_returns_false_for_short_text() -> None:
    store = TextSignatureStore(min_shingles=5)
    assert store.add("p1", "kort tekstje") is False
    assert not store.has("p1")
