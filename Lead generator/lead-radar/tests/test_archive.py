"""Minimal source-page archive — doctrine §01.3.

Every approved lead gets an offline HTML snapshot at approval time. The
archive is the auditor's safety net (§04.4). Failure to capture must NOT
block approval — it's recorded as archive_status="failed" so the gap is
auditable.
"""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import requests

from moderation.archive import archive_source, ARCHIVE_MAX_BYTES


def _mock_response(status: int, body: bytes):
    resp = MagicMock()
    resp.status_code = status
    resp.iter_content = lambda chunk_size=8192: [body]

    def _raise_for_status() -> None:
        if 400 <= status < 600:
            raise requests.exceptions.HTTPError(f"{status} mock error")

    resp.raise_for_status = _raise_for_status
    return resp


def test_archive_success_writes_html_and_meta(tmp_path: Path):
    body = b"<html><body>Hello warmtepomp</body></html>"
    with patch("moderation.archive.requests.get", return_value=_mock_response(200, body)):
        record = archive_source(
            candidate_id="C-001",
            source_url="https://reddit.com/r/x/post/abc",
            output_dir=tmp_path,
        )
    assert record.status == "ok"
    assert record.http_status == 200
    assert record.sha256 == hashlib.sha256(body).hexdigest()
    assert record.bytes == len(body)

    html_path = tmp_path / "C-001" / "source.html"
    meta_path = tmp_path / "C-001" / "meta.json"
    assert html_path.exists()
    assert html_path.read_bytes() == body
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "ok"
    assert meta["sha256"] == record.sha256


def test_archive_http_failure_records_status_failed(tmp_path: Path):
    with patch(
        "moderation.archive.requests.get",
        side_effect=ConnectionError("dns fail"),
    ):
        record = archive_source(
            candidate_id="C-002",
            source_url="https://gone.example.com/post",
            output_dir=tmp_path,
        )
    assert record.status == "failed"
    assert record.sha256 is None
    assert record.path is None
    assert "dns fail" in (record.error or "")
    meta_path = tmp_path / "C-002" / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "failed"


def test_archive_content_too_large_rejected(tmp_path: Path):
    oversized = b"x" * (ARCHIVE_MAX_BYTES + 1)
    with patch(
        "moderation.archive.requests.get",
        return_value=_mock_response(200, oversized),
    ):
        record = archive_source(
            candidate_id="C-003",
            source_url="https://huge.example.com/post",
            output_dir=tmp_path,
        )
    assert record.status == "failed"
    assert "exceeds" in (record.error or "").lower()


def test_archive_creates_directory(tmp_path: Path):
    body = b"<html>tiny</html>"
    with patch("moderation.archive.requests.get", return_value=_mock_response(200, body)):
        archive_source(
            candidate_id="C-004",
            source_url="https://example.com/p",
            output_dir=tmp_path,
        )
    assert (tmp_path / "C-004").is_dir()


def test_archive_http_error_records_status_failed(tmp_path: Path):
    error_body = b"<html><body>404 Not Found</body></html>"
    with patch(
        "moderation.archive.requests.get",
        return_value=_mock_response(404, error_body),
    ):
        record = archive_source(
            candidate_id="C-404",
            source_url="https://example.com/gone",
            output_dir=tmp_path,
        )
    assert record.status == "failed"
    assert record.sha256 is None
    assert record.path is None
    assert record.bytes is None
    assert "404" in (record.error or "")
    html_path = tmp_path / "C-404" / "source.html"
    assert not html_path.exists(), "error-page body must not be archived as ok"
    meta_path = tmp_path / "C-404" / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "failed"


def test_archive_server_error_records_status_failed(tmp_path: Path):
    error_body = b"<html>503 Service Unavailable</html>"
    with patch(
        "moderation.archive.requests.get",
        return_value=_mock_response(503, error_body),
    ):
        record = archive_source(
            candidate_id="C-503",
            source_url="https://example.com/down",
            output_dir=tmp_path,
        )
    assert record.status == "failed"
    assert record.http_status is None
    assert record.sha256 is None
