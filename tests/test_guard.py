import pytest
from typer.testing import CliRunner

from factory import guard
from factory.cli import app


def test_api_key_blocks_startup():
    with pytest.raises(guard.ApiKeySetError):
        guard.check_environment({"ANTHROPIC_API_KEY": "sk-ant-x"})


def test_clean_environment_passes():
    assert guard.check_environment({}) == []


def test_routing_variables_warn():
    warnings = guard.check_environment({"ANTHROPIC_BASE_URL": "http://x"})
    assert warnings and "ANTHROPIC_BASE_URL" in warnings[0]


def test_child_env_strips_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert "ANTHROPIC_API_KEY" not in guard.child_env()


def test_cli_status_refuses_with_key(factory_root, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY" in result.output


def test_cli_status_runs(factory_root):
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "No series yet" in result.output
