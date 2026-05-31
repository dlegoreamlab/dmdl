from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from dmdl import Downloader
from dmdl.config_loader import (
    DEFAULT_CONFIG_DIR,
    load_runtime_config,
    normalize_targets_from_config,
    resolve_default_download_dir,
    resolve_default_result_path,
)
from dmdl.logging import configure_logging



def build_downloader(cfg: dict) -> Downloader:
    defaults = cfg.get("defaults", {})
    return Downloader(
        quality=defaults.get("quality", "1080p"),
        subtitle=defaults.get("subtitle", True),
        thumbnail=defaults.get("thumbnail", True),
        playlist=defaults.get("playlist", False),
        download_dir=resolve_default_download_dir(cfg),
        node_id=defaults.get("node_id", "local"),
        max_concurrency=defaults.get("max_concurrency", 3),
        auto_load_plugins=defaults.get("auto_load_plugins", True),
    )


async def run_from_config(config_path: Path, result_path: Path) -> list[dict]:
    cfg = load_runtime_config(config_path)
    downloader = build_downloader(cfg)

    plugin_import_paths = cfg.get("plugins", [])
    if plugin_import_paths:
        downloader.load_plugins(plugin_import_paths)

    targets = normalize_targets_from_config(cfg)
    results = await downloader.download_many(targets)
    payload = [item.to_dict() for item in results]
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DMDL command line interface")
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_DIR,
        help="설정 JSON 파일 또는 config 폴더 경로",
    )
    parser.add_argument(
        "--result",
        default=None,
        help="실행 결과 JSON 저장 경로. 비우면 설정값 또는 기본값을 사용합니다.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level for DMDL runtime output",
    )
    return parser



def main() -> None:
    args = build_parser().parse_args()
    configure_logging(getattr(logging, str(args.log_level).upper(), logging.INFO))

    config_path = Path(args.config)
    cfg = load_runtime_config(config_path)
    result_path = Path(args.result) if args.result else Path(resolve_default_result_path(config_path, cfg))
    payload = asyncio.run(run_from_config(config_path, result_path))

    for index, item in enumerate(payload, start=1):
        status = "OK" if item["success"] else "FAIL"
        print(f"[{index}/{len(payload)}] {status} :: {item['source_url']}")
        if item["success"]:
            print(f"  saved_path: {item['saved_path']}")
        else:
            print(f"  error: {item['error']}")

    print(f"\nSaved summary -> {result_path}")


if __name__ == "__main__":
    main()
