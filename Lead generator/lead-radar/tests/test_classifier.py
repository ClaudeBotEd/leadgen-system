"""Regression-tests voor intent_classifier.classify_post_kind + is_potential_lead."""
from __future__ import annotations

import pytest

from consumer.processor.intent_classifier import classify_post_kind, is_potential_lead

from tests.canonical_corpus import ALL_POSTS


@pytest.mark.parametrize("post", ALL_POSTS, ids=lambda p: p["id"])
def test_classifier_kind(post: dict) -> None:
    full = f"{post['title']}\n\n{post['text']}".strip()
    kind = classify_post_kind(full)
    assert kind == post["expected"]["classifier_kind"], (
        f"post={post['id']!r} expected kind={post['expected']['classifier_kind']} "
        f"but got {kind}"
    )


@pytest.mark.parametrize("post", ALL_POSTS, ids=lambda p: p["id"])
def test_classifier_keep(post: dict) -> None:
    full = f"{post['title']}\n\n{post['text']}".strip()
    keep = is_potential_lead(full)
    assert keep == post["expected"]["classifier_keep"], (
        f"post={post['id']!r} expected keep={post['expected']['classifier_keep']} "
        f"but got {keep}"
    )
