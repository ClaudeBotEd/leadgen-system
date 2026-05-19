import pytest

from delivery.vocab_lint import (
    BANNED_SUBSTRINGS,
    REQUIRED_SUBSTITUTIONS,
    check_no_banned_terms,
)


def test_clean_text_returns_empty():
    text = "Marieke reviewde een Tweakers-post uit regio Amsterdam."
    assert check_no_banned_terms(text) == []


def test_flags_ai_in_chrome():
    violations = check_no_banned_terms("Powered by AI scoring")
    assert any("AI" in v.matched for v in violations)


def test_flags_model_name():
    violations = check_no_banned_terms("Powered by GPT-4")
    assert any("GPT" in v.matched for v in violations)


def test_flags_paraphrase_marker():
    violations = check_no_banned_terms("AI-prediction: high intent for heat pump")
    kinds = {v.kind for v in violations}
    assert "ai_chrome" in kinds or "paraphrase_signal" in kinds


def test_flags_percentage_score():
    violations = check_no_banned_terms("Lead score: 87%")
    assert any(v.kind == "score_numeric" for v in violations)


def test_flags_qualified_lead_vocab():
    violations = check_no_banned_terms("Hierbij een qualified lead voor u.")
    assert any(v.kind == "vocab_banned" and "qualified" in v.matched.lower() for v in violations)


def test_flags_noreply_alias():
    violations = check_no_banned_terms("Antwoord aan noreply@lead-radar.nl")
    assert any(v.kind == "sender_alias" for v in violations)


def test_flags_emoji_in_subject():
    violations = check_no_banned_terms("🔥 Last chance!")
    assert any(v.kind == "urgency_emoji" for v in violations)


def test_substitutions_map_defined():
    assert REQUIRED_SUBSTITUTIONS["klant"] == "installateur"


def test_word_boundary_for_ai_avoids_false_positive():
    assert check_no_banned_terms("De AIB-norm is gehaald.") == []


def test_banned_substrings_is_immutable():
    with pytest.raises((AttributeError, TypeError)):
        BANNED_SUBSTRINGS.add("foo")  # type: ignore[attr-defined]
