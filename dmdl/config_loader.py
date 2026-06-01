from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CONFIG_DIR = "config"
DEFAULT_MAIN_CONFIG_NAMES = ("settings.json", "config.json")
DEFAULT_TARGET_FILE_NAMES = ("links.json", "targets.json")
DEFAULT_TARGET_DIR_NAMES = ("links", "targets")


def load_runtime_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if config_path.is_dir():
        return _load_from_directory(config_path)
    return _load_json_mapping(config_path)



def resolve_default_result_path(config_path: str | Path, cfg: dict[str, Any]) -> str:
    configured = (
        cfg.get("results", {}).get("file")
        or cfg.get("paths", {}).get("results_file")
        or cfg.get("result_file")
    )
    if configured:
        return str(configured)

    base_path = Path(config_path)
    if base_path.is_dir():
        return str(base_path / "download_results.json")
    return "download_results.json"



def resolve_default_download_dir(cfg: dict[str, Any]) -> str:
    return str(
        cfg.get("paths", {}).get("download_dir")
        or cfg.get("defaults", {}).get("download_dir")
        or "downloads"
    )



def resolve_target_output_dir(target: dict[str, Any], cfg: dict[str, Any]) -> str:
    if target.get("output_dir"):
        return str(target["output_dir"])

    paths_cfg = dict(cfg.get("paths", {}))
    named_paths = dict(paths_cfg.get("named", {}))
    path_key = target.get("path_key")
    if path_key and path_key in named_paths:
        return str(named_paths[path_key])

    adapter_hint = target.get("adapter_hint")
    by_adapter_hint = dict(paths_cfg.get("by_adapter_hint", {}))
    if adapter_hint and adapter_hint in by_adapter_hint:
        return str(by_adapter_hint[adapter_hint])

    requested_type = target.get("requested_type")
    by_requested_type = dict(paths_cfg.get("by_requested_type", {}))
    if requested_type and requested_type in by_requested_type:
        return str(by_requested_type[requested_type])

    return resolve_default_download_dir(cfg)



def normalize_targets_from_config(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    targets = cfg.get("targets")
    if isinstance(targets, list) and targets:
        return [_normalize_target(dict(item), cfg) for item in targets]

    if cfg.get("url"):
        return [
            _normalize_target(
                {
                    "url": cfg["url"],
                    "requested_type": cfg.get("requested_type"),
                    "output_dir": cfg.get("output_dir"),
                    "adapter_hint": cfg.get("adapter_hint"),
                    "quality": cfg.get("quality"),
                    "subtitle": cfg.get("subtitle"),
                    "subtitle_langs": cfg.get("subtitle_langs"),
                    "subtitle_format": cfg.get("subtitle_format"),
                    "format_selector": cfg.get("format_selector"),
                    "merge_output_format": cfg.get("merge_output_format"),
                    "thumbnail": cfg.get("thumbnail"),
                    "playlist": cfg.get("playlist"),
                    "options": cfg.get("options", {}),
                    "context": cfg.get("context", {}),
                    "priority": cfg.get("priority", 100),
                    "path_key": cfg.get("path_key"),
                },
                cfg,
            )
        ]

    raise ValueError("설정 파일에 'targets' 목록 또는 최상위 'url' 값이 필요합니다.")



def _load_from_directory(config_dir: Path) -> dict[str, Any]:
    main_config: dict[str, Any] = {}
    main_file = _find_first_existing(config_dir, DEFAULT_MAIN_CONFIG_NAMES)
    if main_file:
        main_config = _load_json_mapping(main_file)

    include_paths = list(_iter_explicit_include_paths(config_dir, main_config))
    include_paths.extend(_iter_auto_target_paths(config_dir))

    merged_targets: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for candidate in include_paths:
        resolved = candidate.resolve()
        if resolved in seen or not candidate.exists() or candidate == main_file:
            continue
        seen.add(resolved)
        merged_targets.extend(_extract_targets(candidate))

    if merged_targets:
        main_config["targets"] = [*main_config.get("targets", []), *merged_targets]

    return main_config



def _iter_explicit_include_paths(config_dir: Path, cfg: dict[str, Any]) -> Iterable[Path]:
    for key in ("include", "includes", "target_files"):
        raw = cfg.get(key)
        if isinstance(raw, str) and raw.strip():
            yield config_dir / raw
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and item.strip():
                    yield config_dir / item



def _iter_auto_target_paths(config_dir: Path) -> Iterable[Path]:
    for name in DEFAULT_TARGET_FILE_NAMES:
        candidate = config_dir / name
        if candidate.exists():
            yield candidate

    for directory_name in DEFAULT_TARGET_DIR_NAMES:
        directory = config_dir / directory_name
        if directory.exists() and directory.is_dir():
            for candidate in sorted(directory.glob("*.json")):
                yield candidate

    for pattern in ("*.links.json", "*.targets.json"):
        for candidate in sorted(config_dir.glob(pattern)):
            yield candidate



def _normalize_target(target: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(target)
    normalized.setdefault("options", {})
    normalized.setdefault("context", {})
    normalized.setdefault("priority", 100)
    normalized["output_dir"] = resolve_target_output_dir(normalized, cfg)
    return normalized



def _extract_targets(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("targets"), list):
            return [dict(item) for item in payload["targets"] if isinstance(item, dict)]
        if payload.get("url"):
            return [dict(payload)]
    raise ValueError(f"지원하지 않는 타깃 JSON 형식입니다: {path}")



def _load_json_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{path} 파일을 찾을 수 없습니다.")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"설정 파일은 JSON 객체여야 합니다: {path}")
    return payload



def _find_first_existing(base_dir: Path, names: Iterable[str]) -> Path | None:
    for name in names:
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    return None
