"""Tests for ado_dashboard.config — 4-layer resolution."""

import pytest

from ado_dashboard import config


@pytest.fixture(autouse=True)
def reset_config_state(monkeypatch):
    """Reset module-level config state between tests."""
    original_values = {
        "ORG_URL": config.ORG_URL,
        "PROJECT": config.PROJECT,
        "USER_EMAIL": config.USER_EMAIL,
        "PROJECTS": config.PROJECTS[:],
        "TRIAGE_SCRIPT_PATH": config.TRIAGE_SCRIPT_PATH,
        "TRIAGE_BOARD": config.TRIAGE_BOARD,
        "TRIAGE_BOARD_OPTIONS": config.TRIAGE_BOARD_OPTIONS[:],
        "TRIAGE_PR_REPO": config.TRIAGE_PR_REPO,
        "INVESTIGATIONS_DIR": config.INVESTIGATIONS_DIR,
        "INVESTIGATION_MODEL": config.INVESTIGATION_MODEL,
        "INVESTIGATION_AGENT": config.INVESTIGATION_AGENT,
        "AI_TRIAGE_MODE": config.AI_TRIAGE_MODE,
        "TRIAGE_CACHE_DIR": config.TRIAGE_CACHE_DIR,
        "TRIAGE_CACHE_MAX_AGE_SECONDS": config.TRIAGE_CACHE_MAX_AGE_SECONDS,
        "COPILOT_SESSION_DIR": config.COPILOT_SESSION_DIR,
        "SESSION_MAX_AGE_DAYS": config.SESSION_MAX_AGE_DAYS,
    }
    yield
    # Restore original values
    config.ORG_URL = original_values["ORG_URL"]
    config.PROJECT = original_values["PROJECT"]
    config.USER_EMAIL = original_values["USER_EMAIL"]
    config.PROJECTS = original_values["PROJECTS"]
    config.TRIAGE_SCRIPT_PATH = original_values["TRIAGE_SCRIPT_PATH"]
    config.TRIAGE_BOARD = original_values["TRIAGE_BOARD"]
    config.TRIAGE_BOARD_OPTIONS = original_values["TRIAGE_BOARD_OPTIONS"]
    config.TRIAGE_PR_REPO = original_values["TRIAGE_PR_REPO"]
    config.INVESTIGATIONS_DIR = original_values["INVESTIGATIONS_DIR"]
    config.INVESTIGATION_MODEL = original_values["INVESTIGATION_MODEL"]
    config.INVESTIGATION_AGENT = original_values["INVESTIGATION_AGENT"]
    config.AI_TRIAGE_MODE = original_values["AI_TRIAGE_MODE"]
    config.TRIAGE_CACHE_DIR = original_values["TRIAGE_CACHE_DIR"]
    config.TRIAGE_CACHE_MAX_AGE_SECONDS = original_values["TRIAGE_CACHE_MAX_AGE_SECONDS"]
    config.COPILOT_SESSION_DIR = original_values["COPILOT_SESSION_DIR"]
    config.SESSION_MAX_AGE_DAYS = original_values["SESSION_MAX_AGE_DAYS"]


# --- apply_overrides() tests ------------------------------------------------

def test_apply_overrides_with_org_url():
    """CLI org_url overrides module value."""
    class Namespace:
        org_url = "https://custom.example.com"
    config.apply_overrides(Namespace())
    assert config.ORG_URL == "https://custom.example.com"


def test_apply_overrides_with_project():
    """CLI project overrides module value."""
    class Namespace:
        project = "CustomProject"
    config.apply_overrides(Namespace())
    assert config.PROJECT == "CustomProject"


def test_apply_overrides_with_user_email():
    """CLI user_email overrides module value."""
    class Namespace:
        user_email = "user@custom.com"
    config.apply_overrides(Namespace())
    assert config.USER_EMAIL == "user@custom.com"


def test_apply_overrides_with_projects_string():
    """CLI projects as comma-separated string splits into list."""
    class Namespace:
        projects = "Proj1, Proj2, Proj3"
    config.apply_overrides(Namespace())
    assert config.PROJECTS == ["Proj1", "Proj2", "Proj3"]


def test_apply_overrides_with_projects_list():
    """CLI projects as list is used directly."""
    class Namespace:
        projects = ["Proj1", "Proj2"]
    config.apply_overrides(Namespace())
    assert config.PROJECTS == ["Proj1", "Proj2"]


def test_apply_overrides_with_triage_board():
    """CLI triage_board overrides module value."""
    class Namespace:
        triage_board = "https://example.com/board"
    config.apply_overrides(Namespace())
    assert config.TRIAGE_BOARD == "https://example.com/board"


def test_apply_overrides_ignores_none():
    """Attributes that are None are ignored."""
    class Namespace:
        org_url = None
        project = None
        user_email = None
        projects = None
        triage_board = None
    original_org = config.ORG_URL
    config.apply_overrides(Namespace())
    assert config.ORG_URL == original_org


def test_apply_overrides_ignores_missing_attrs():
    """Missing attributes are ignored."""
    class Namespace:
        pass
    original_org = config.ORG_URL
    config.apply_overrides(Namespace())
    assert config.ORG_URL == original_org


# --- load_from_file() tests -------------------------------------------------

def test_load_from_file_applies_ado_org_url(monkeypatch):
    """load_from_file applies ado_org_url when env var not set."""
    monkeypatch.delenv("ADO_ORG_URL", raising=False)
    config.load_from_file({"ado_org_url": "https://file.example.com"})
    assert config.ORG_URL == "https://file.example.com"


def test_load_from_file_respects_env_var(monkeypatch):
    """load_from_file skips ado_org_url when ADO_ORG_URL env var is set."""
    monkeypatch.setenv("ADO_ORG_URL", "https://env.example.com")
    config.ORG_URL = "https://env.example.com"
    config.load_from_file({"ado_org_url": "https://file.example.com"})
    assert config.ORG_URL == "https://env.example.com"


def test_load_from_file_applies_ado_project(monkeypatch):
    """load_from_file applies ado_project when env var not set."""
    monkeypatch.delenv("ADO_PROJECT", raising=False)
    config.load_from_file({"ado_project": "FileProject"})
    assert config.PROJECT == "FileProject"


def test_load_from_file_applies_user_email(monkeypatch):
    """load_from_file applies user_email when env var not set."""
    monkeypatch.delenv("ADO_USER_EMAIL", raising=False)
    config.load_from_file({"user_email": "file@example.com"})
    assert config.USER_EMAIL == "file@example.com"


def test_load_from_file_applies_ado_projects(monkeypatch):
    """load_from_file always applies ado_projects (no dedicated env var)."""
    config.load_from_file({"ado_projects": ["Proj1", "Proj2"]})
    assert config.PROJECTS == ["Proj1", "Proj2"]


def test_load_from_file_applies_triage_script_path(monkeypatch):
    """load_from_file applies triage_script_path when env var not set."""
    monkeypatch.delenv("TRIAGE_SCRIPT_PATH", raising=False)
    config.load_from_file({"triage_script_path": "/custom/script.ps1"})
    assert config.TRIAGE_SCRIPT_PATH == "/custom/script.ps1"


def test_load_from_file_applies_triage_board(monkeypatch):
    """load_from_file applies triage_board when env var not set."""
    monkeypatch.delenv("TRIAGE_BOARD", raising=False)
    config.load_from_file({"triage_board": "https://example.com/board"})
    assert config.TRIAGE_BOARD == "https://example.com/board"


def test_load_from_file_applies_triage_board_options(monkeypatch):
    """load_from_file applies triage_board_options."""
    config.load_from_file({"triage_board_options": [["Board1", "url1"], ["Board2", "url2"]]})
    assert config.TRIAGE_BOARD_OPTIONS == [("Board1", "url1"), ("Board2", "url2")]


def test_load_from_file_applies_investigations_dir(monkeypatch):
    """load_from_file applies investigations_dir when env var not set."""
    monkeypatch.delenv("INVESTIGATIONS_DIR", raising=False)
    config.load_from_file({"investigations_dir": "/custom/investigations"})
    assert config.INVESTIGATIONS_DIR == "/custom/investigations"


def test_load_from_file_applies_ai_triage_mode(monkeypatch):
    """load_from_file applies ai_triage_mode when env var not set."""
    monkeypatch.delenv("AI_TRIAGE_MODE", raising=False)
    config.load_from_file({"ai_triage_mode": "off"})
    assert config.AI_TRIAGE_MODE == "off"


# --- URL helpers ------------------------------------------------------------

def test_pr_url_builds_correct_url():
    """pr_url() returns expected format."""
    config.ORG_URL = "https://dev.azure.com/myorg"
    config.PROJECT = "MyProject"
    url = config.pr_url("MyRepo", 123)
    assert url == "https://dev.azure.com/myorg/MyProject/_git/MyRepo/pullrequest/123"


def test_work_item_url_builds_correct_url():
    """work_item_url() returns expected format."""
    config.ORG_URL = "https://dev.azure.com/myorg"
    config.PROJECT = "MyProject"
    url = config.work_item_url(456)
    assert url == "https://dev.azure.com/myorg/MyProject/_workitems/edit/456"
