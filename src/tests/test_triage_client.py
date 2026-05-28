"""Tests for ado_dashboard.triage_client — negative test for missing script."""

import pytest

from ado_dashboard import config, triage_client


def test_resolve_script_path_raises_when_not_configured(monkeypatch):
    """_resolve_script_path raises clear error when config is empty."""
    monkeypatch.setattr(config, "TRIAGE_SCRIPT_PATH", "")
    with pytest.raises(triage_client.TriageClientError) as exc_info:
        triage_client._resolve_script_path()
    assert "not configured" in str(exc_info.value).lower()
    assert "triage_script_path" in str(exc_info.value).lower()


def test_resolve_script_path_raises_when_not_found(monkeypatch, tmp_path):
    """_resolve_script_path raises clear error when script doesn't exist."""
    nonexistent = tmp_path / "nonexistent.ps1"
    monkeypatch.setattr(config, "TRIAGE_SCRIPT_PATH", str(nonexistent))
    with pytest.raises(triage_client.TriageClientError) as exc_info:
        triage_client._resolve_script_path()
    assert "not found" in str(exc_info.value).lower()
