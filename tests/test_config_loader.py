import json
from pathlib import Path

from dmdl.config_loader import (
    load_runtime_config,
    normalize_targets_from_config,
    resolve_default_download_dir,
    resolve_default_result_path,
)



def test_load_runtime_config_merges_targets_from_config_directory(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.json").write_text(
        json.dumps(
            {
                "defaults": {"max_concurrency": 2},
                "paths": {
                    "download_dir": "downloads",
                    "by_requested_type": {"pdf": "downloads/docs"},
                },
                "include": ["links.json"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "links.json").write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "url": "https://example.com/a.pdf",
                        "requested_type": "pdf",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cfg = load_runtime_config(config_dir)
    targets = normalize_targets_from_config(cfg)

    assert len(targets) == 1
    assert targets[0]["url"] == "https://example.com/a.pdf"
    assert targets[0]["output_dir"] == "downloads/docs"



def test_load_runtime_config_supports_named_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "paths": {
                    "download_dir": "downloads",
                    "named": {"private_room": "downloads/telegram/private_room"},
                },
                "targets": [
                    {
                        "url": "https://t.me/c/1234567890/42",
                        "requested_type": "video",
                        "adapter_hint": "telegram",
                        "path_key": "private_room",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cfg = load_runtime_config(config_path)
    targets = normalize_targets_from_config(cfg)

    assert targets[0]["output_dir"] == "downloads/telegram/private_room"



def test_default_paths_resolve_from_config_directory() -> None:
    cfg = {
        "paths": {
            "download_dir": "downloads/base",
            "results_file": "artifacts/results.json",
        }
    }

    assert resolve_default_download_dir(cfg) == "downloads/base"
    assert resolve_default_result_path(Path("config"), cfg) == "artifacts/results.json"
