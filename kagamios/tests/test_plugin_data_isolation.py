from pathlib import Path

import kagami
from kagami.store.run import open_run


def test_run_data_never_lands_inside_the_installed_plugin_package(tmp_path):
    plugin_package_root = Path(kagami.__file__).resolve().parent

    result = open_run(run_id="run-isolation", output_root=tmp_path / "_kagami-output")
    run_dir = Path(result["path"]).resolve()

    assert plugin_package_root not in run_dir.parents
    assert run_dir != plugin_package_root
    assert not str(run_dir).startswith(str(plugin_package_root))
