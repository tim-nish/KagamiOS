from kagami.config import load_config


def test_load_config_returns_empty_dict_when_no_config_file(tmp_path):
    assert load_config(tmp_path) == {}


def test_load_config_reads_yaml_file(tmp_path):
    (tmp_path / "config.yaml").write_text("literature_provider: arxiv\n")
    assert load_config(tmp_path) == {"literature_provider": "arxiv"}
