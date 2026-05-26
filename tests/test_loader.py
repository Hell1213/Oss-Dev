import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from config.loader import (
    get_system_config_path,
    _parse_toml,
    _get_project_config,
    _merge_dicts,
    load_config,
)
from utils.errors import ConfigError
def test_load_config_from_system_config(tmp_path):
    system_toml = tmp_path / "config.toml"
    system_toml.write_bytes(b'[llm]\nmodel = "gpt-4"\n')

    with patch("config.loader.get_system_config_path", return_value=system_toml):
        with patch("config.loader._get_project_config", return_value=None):
            with patch("config.loader.Config") as MockConfig:
                MockConfig.return_value = MagicMock()
                load_config(tmp_path)
                call_kwargs = MockConfig.call_args[1]
                assert call_kwargs.get("llm", {}).get("model") == "gpt-4"
def test_load_config_skips_missing_system_config(tmp_path):
    missing_path = tmp_path / "nonexistent.toml"

    with patch("config.loader.get_system_config_path", return_value=missing_path):
        with patch("config.loader._get_project_config", return_value=None):
            with patch("config.loader.Config") as MockConfig:
                MockConfig.return_value = MagicMock()
                load_config(tmp_path)
                MockConfig.assert_called_once()
def test_load_config_from_project_config(tmp_path):
    agent_dir = tmp_path / ".ai-agent"
    agent_dir.mkdir()
    project_toml = agent_dir / "config.toml"
    project_toml.write_bytes(b'[llm]\nmodel = "gpt-3.5"\n')

    missing_system = tmp_path / "nonexistent.toml"

    with patch("config.loader.get_system_config_path", return_value=missing_system):
        with patch("config.loader.Config") as MockConfig:
            MockConfig.return_value = MagicMock()
            load_config(tmp_path)
            call_kwargs = MockConfig.call_args[1]
            assert call_kwargs.get("llm", {}).get("model") == "gpt-3.5"
def test_project_config_overrides_system_config(tmp_path):
    system_toml = tmp_path / "system.toml"
    system_toml.write_bytes(b'[llm]\nmodel = "gpt-4"\n')

    agent_dir = tmp_path / ".ai-agent"
    agent_dir.mkdir()
    project_toml = agent_dir / "config.toml"
    project_toml.write_bytes(b'[llm]\nmodel = "gpt-3.5"\n')

    with patch("config.loader.get_system_config_path", return_value=system_toml):
        with patch("config.loader.Config") as MockConfig:
            MockConfig.return_value = MagicMock()
            load_config(tmp_path)
            call_kwargs = MockConfig.call_args[1]
            assert call_kwargs.get("llm", {}).get("model") == "gpt-3.5"
def test_parse_toml_raises_config_error_on_invalid_toml(tmp_path):
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_bytes(b"invalid = [unclosed")
    with pytest.raises(ConfigError):
        _parse_toml(bad_toml)
def test_parse_toml_raises_config_error_on_missing_file(tmp_path):
    missing = tmp_path / "missing.toml"
    with pytest.raises(ConfigError):
        _parse_toml(missing)
def test_parse_toml_success(tmp_path):
    good_toml = tmp_path / "good.toml"
    good_toml.write_bytes(b'[section]\nkey = "value"\n')
    result = _parse_toml(good_toml)
    assert result == {"section": {"key": "value"}}
def test_load_config_skips_invalid_system_config(tmp_path, caplog):
    bad_system = tmp_path / "bad.toml"
    bad_system.write_bytes(b"invalid = [unclosed")

    with patch("config.loader.get_system_config_path", return_value=bad_system):
        with patch("config.loader._get_project_config", return_value=None):
            with patch("config.loader.Config") as MockConfig:
                MockConfig.return_value = MagicMock()
                load_config(tmp_path)
                MockConfig.assert_called_once()
def test_get_project_config_returns_none_when_no_agent_dir(tmp_path):
    result = _get_project_config(tmp_path)
    assert result is None
def test_get_project_config_returns_none_when_no_config_file(tmp_path):
    agent_dir = tmp_path / ".ai-agent"
    agent_dir.mkdir()
    result = _get_project_config(tmp_path)
    assert result is None
def test_get_project_config_returns_path_when_exists(tmp_path):
    agent_dir = tmp_path / ".ai-agent"
    agent_dir.mkdir()
    config_file = agent_dir / "config.toml"
    config_file.write_bytes(b"")
    result = _get_project_config(tmp_path)
    assert result == config_file
def test_merge_dicts_override_simple_value():
    base = {"key": "base_value"}
    override = {"key": "new_value"}
    result = _merge_dicts(base, override)
    assert result["key"] == "new_value"
def test_merge_dicts_deep_merge():
    base = {"llm": {"model": "gpt-4", "temperature": 0.7}}
    override = {"llm": {"model": "gpt-3.5"}}
    result = _merge_dicts(base, override)
    assert result["llm"]["model"] == "gpt-3.5"
    assert result["llm"]["temperature"] == 0.7
def test_merge_dicts_does_not_modify_base():
    base = {"key": "original"}
    override = {"key": "changed"}
    _merge_dicts(base, override)
    assert base["key"] == "original"
def test_environment_variable_override(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_AGENT_MODEL", "gpt-env")
    missing_system = tmp_path / "nonexistent.toml"

    with patch("config.loader.get_system_config_path", return_value=missing_system):
        with patch("config.loader._get_project_config", return_value=None):
            with patch("config.loader.Config") as MockConfig:
                MockConfig.return_value = MagicMock()
                load_config(tmp_path)
                MockConfig.assert_called_once()
