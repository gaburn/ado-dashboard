"""Tests for ado_dashboard.investigation — launcher adapter interface."""

import pytest

from ado_dashboard import investigation


def test_noop_launcher_board_prompt():
    """NoOpLauncher.build_board_prompt returns generic string."""
    launcher = investigation.NoOpLauncher()
    prompt = launcher.build_board_prompt(
        "https://dev.azure.com/org/proj/_boards/board/t/team", "My Board"
    )
    assert "My Board" in prompt
    assert "https://dev.azure.com/org/proj/_boards/board/t/team" in prompt
    assert "P1" in prompt


def test_noop_launcher_item_prompt_basic():
    """NoOpLauncher.build_item_prompt returns generic string."""
    launcher = investigation.NoOpLauncher()
    prompt = launcher.build_item_prompt(123, "My Item", "https://example.com/board")
    assert "123" in prompt
    assert "My Item" in prompt


def test_noop_launcher_item_prompt_with_category():
    """NoOpLauncher.build_item_prompt includes category when provided."""
    launcher = investigation.NoOpLauncher()
    prompt = launcher.build_item_prompt(
        123, "My Item", "https://example.com/board", category="Bug / Behavior"
    )
    assert "Bug / Behavior" in prompt


def test_noop_launcher_item_prompt_with_priority():
    """NoOpLauncher.build_item_prompt includes priority label when provided."""
    launcher = investigation.NoOpLauncher()
    prompt = launcher.build_item_prompt(
        123, "My Item", "https://example.com/board", priority_label="P1"
    )
    assert "P1" in prompt


def test_noop_launcher_ai_triage_prompt():
    """NoOpLauncher.build_ai_triage_prompt includes board URL and output path."""
    launcher = investigation.NoOpLauncher()
    prompt = launcher.build_ai_triage_prompt(
        "https://example.com/board", "/tmp/output.json"
    )
    assert "https://example.com/board" in prompt
    assert "/tmp/output.json" in prompt
    assert "JSON" in prompt


def test_noop_launcher_launch_returns_failure():
    """NoOpLauncher.launch always returns (False, error message)."""
    launcher = investigation.NoOpLauncher()
    success, msg = launcher.launch("test prompt")
    assert success is False
    assert "backend" in msg.lower() and "configured" in msg.lower()


def test_noop_launcher_discover_models_returns_empty():
    """NoOpLauncher.discover_models returns empty list."""
    launcher = investigation.NoOpLauncher()
    models = launcher.discover_models()
    assert models == []


def test_noop_launcher_discover_agents_returns_empty():
    """NoOpLauncher.discover_agents returns empty list."""
    launcher = investigation.NoOpLauncher()
    agents = launcher.discover_agents()
    assert agents == []


def test_get_launcher_returns_default():
    """get_launcher() returns default NoOpLauncher when nothing configured."""
    launcher = investigation.get_launcher()
    assert isinstance(launcher, investigation.NoOpLauncher)


def test_set_launcher_replaces_default():
    """set_launcher() replaces the active launcher."""
    custom = investigation.NoOpLauncher()
    investigation.set_launcher(custom)
    launcher = investigation.get_launcher()
    assert launcher is custom


@pytest.mark.skipif(
    not investigation.shutil.which("agency"),
    reason="agency CLI not on PATH",
)
def test_agency_launcher_board_prompt():
    """AgencyLauncher.build_board_prompt mentions triage and prioritization."""
    launcher = investigation.AgencyLauncher()
    prompt = launcher.build_board_prompt(
        "https://dev.azure.com/org/proj/_boards/board/t/team", "My Board"
    )
    assert "My Board" in prompt
    assert "triage" in prompt.lower() or "investigate" in prompt.lower()


@pytest.mark.skipif(
    not investigation.shutil.which("agency"),
    reason="agency CLI not on PATH",
)
def test_agency_launcher_item_prompt_basic():
    """AgencyLauncher.build_item_prompt returns a basic prompt."""
    launcher = investigation.AgencyLauncher()
    prompt = launcher.build_item_prompt(123, "My Item", "https://example.com/board")
    assert "123" in prompt
    assert "My Item" in prompt


@pytest.mark.skipif(
    not investigation.shutil.which("agency"),
    reason="agency CLI not on PATH",
)
def test_agency_launcher_ai_triage_prompt():
    """AgencyLauncher.build_ai_triage_prompt includes JSON schema."""
    launcher = investigation.AgencyLauncher()
    prompt = launcher.build_ai_triage_prompt(
        "https://example.com/board", "/tmp/output.json"
    )
    assert "https://example.com/board" in prompt
    assert "/tmp/output.json" in prompt
    assert "JSON" in prompt
