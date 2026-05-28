"""Tests for ado_dashboard.investigation_prompts — pure prompt builders."""

import pytest
from ado_dashboard import investigation_prompts


def test_board_key_from_url_extracts_team():
    """board_key_from_url extracts team from standard ADO board URL."""
    url = "https://dev.azure.com/org/proj/_boards/board/t/MyTeam/Stories"
    key = investigation_prompts.board_key_from_url(url)
    assert key == "myteam"


def test_board_key_from_url_with_spaces():
    """board_key_from_url handles URL-encoded team names."""
    url = "https://dev.azure.com/org/proj/_boards/board/t/My%20Team/Stories"
    key = investigation_prompts.board_key_from_url(url)
    assert key == "my-team"


def test_board_key_from_url_no_match():
    """board_key_from_url returns 'board' when URL doesn't match."""
    url = "https://example.com/not-a-board"
    key = investigation_prompts.board_key_from_url(url)
    assert key == "board"


def test_board_key_from_url_no_team_segment():
    """board_key_from_url returns 'board' when no team segment present."""
    url = "https://dev.azure.com/org/proj/_boards/board/t/"
    key = investigation_prompts.board_key_from_url(url)
    assert key == "board"


def test_build_board_investigation_prompt():
    """build_board_investigation_prompt delegates to launcher."""
    prompt = investigation_prompts.build_board_investigation_prompt(
        "https://dev.azure.com/org/proj/_boards/board/t/team", "My Board"
    )
    assert "My Board" in prompt
    assert "https://dev.azure.com/org/proj/_boards/board/t/team" in prompt


def test_build_item_investigation_prompt():
    """build_item_investigation_prompt delegates to launcher."""
    prompt = investigation_prompts.build_item_investigation_prompt(
        123, "My Item", "https://example.com/board"
    )
    assert "123" in prompt
    assert "My Item" in prompt


def test_build_item_investigation_prompt_with_category():
    """build_item_investigation_prompt includes category when provided."""
    prompt = investigation_prompts.build_item_investigation_prompt(
        123, "My Item", "https://example.com/board", category="Bug / Behavior"
    )
    assert "Bug / Behavior" in prompt


def test_build_item_investigation_prompt_with_priority():
    """build_item_investigation_prompt includes priority when provided."""
    prompt = investigation_prompts.build_item_investigation_prompt(
        123, "My Item", "https://example.com/board", priority_label="P1"
    )
    assert "P1" in prompt


def test_build_ai_triage_prompt():
    """build_ai_triage_prompt mentions board URL, output path, and JSON schema."""
    prompt = investigation_prompts.build_ai_triage_prompt(
        "https://example.com/board", "/tmp/output.json"
    )
    assert "https://example.com/board" in prompt
    assert "/tmp/output.json" in prompt
    assert "JSON" in prompt


def test_build_ai_triage_prompt_includes_schema_fields():
    """build_ai_triage_prompt includes key JSON schema field names."""
    prompt = investigation_prompts.build_ai_triage_prompt(
        "https://example.com/board", "/tmp/output.json"
    )
    # Check for key fields mentioned in the schema
    assert "id" in prompt
    assert "category" in prompt
    assert "priority" in prompt
    assert "why" in prompt
    assert "action_plan" in prompt
