"""Unit tests for demo_bundle.sample_receipt."""
from __future__ import annotations

from demo_bundle.sample_receipt import render_sample_receipt_html


class TestRenderSampleReceiptHtml:
    def test_returns_html_with_canonical_fields(self):
        html = render_sample_receipt_html()
        assert isinstance(html, str)
        assert "warmtepomp" in html.lower()
        assert "Sem" in html

    def test_renders_non_trivial_length(self):
        html = render_sample_receipt_html()
        assert len(html) > 200
