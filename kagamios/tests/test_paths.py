from pathlib import Path

from kagami.paths import DEFAULT_OUTPUT_ROOT_DIRNAME, OUTPUT_ROOT_ENV_VAR, resolve_output_root


def test_resolve_output_root_defaults_relative_to_given_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv(OUTPUT_ROOT_ENV_VAR, raising=False)

    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()

    assert resolve_output_root(project_a) == project_a / DEFAULT_OUTPUT_ROOT_DIRNAME
    assert resolve_output_root(project_b) == project_b / DEFAULT_OUTPUT_ROOT_DIRNAME


def test_resolve_output_root_honors_env_override_as_absolute_path(tmp_path, monkeypatch):
    override = tmp_path / "custom-output"
    monkeypatch.setenv(OUTPUT_ROOT_ENV_VAR, str(override))

    assert resolve_output_root(tmp_path / "any-project") == override


def test_resolve_output_root_honors_env_override_as_relative_path(tmp_path, monkeypatch):
    monkeypatch.setenv(OUTPUT_ROOT_ENV_VAR, "custom-relative-output")

    project = tmp_path / "project"
    assert resolve_output_root(project) == project / "custom-relative-output"


def test_resolve_output_root_uses_real_cwd_when_none_given(monkeypatch, tmp_path):
    monkeypatch.delenv(OUTPUT_ROOT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)

    assert resolve_output_root() == Path.cwd() / DEFAULT_OUTPUT_ROOT_DIRNAME
