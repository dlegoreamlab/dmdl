from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from dmdl import Downloader
from dmdl.logging import configure_logging


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Copy config.json.example to config.json and edit it first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def build_downloader(cfg: dict) -> Downloader:
    defaults = cfg.get("defaults", {})
    return Downloader(
        quality=defaults.get("quality", "1080p"),
        subtitle=defaults.get("subtitle", True),
        thumbnail=defaults.get("thumbnail", True),
        playlist=defaults.get("playlist", False),
        download_dir=defaults.get("download_dir", "downloads"),
        node_id=defaults.get("node_id", "local"),
        max_concurrency=defaults.get("max_concurrency", 3),
        auto_load_plugins=defaults.get("auto_load_plugins", True),
    )


def normalize_targets(cfg: dict) -> list[dict]:
    targets = cfg.get("targets")
    if isinstance(targets, list) and targets:
        return targets

    if cfg.get("url"):
        return [
            {
                "url": cfg["url"],
                "requested_type": cfg.get("requested_type"),
                "output_dir": cfg.get("output_dir"),
                "adapter_hint": cfg.get("adapter_hint"),
                "quality": cfg.get("quality"),
                "subtitle": cfg.get("subtitle"),
                "thumbnail": cfg.get("thumbnail"),
                "playlist": cfg.get("playlist"),
                "options": cfg.get("options", {}),
                "context": cfg.get("context", {}),
                "priority": cfg.get("priority", 100),
            }
        ]

    raise ValueError("config.json must contain 'targets' or a top-level 'url'.")


async def run_from_config(config_path: Path, result_path: Path) -> list[dict]:
    cfg = load_config(config_path)
    downloader = build_downloader(cfg)

    plugin_import_paths = cfg.get("plugins", [])
    if plugin_import_paths:
        downloader.load_plugins(plugin_import_paths)

    targets = normalize_targets(cfg)
    results = await downloader.download_many(targets)
    payload = [item.to_dict() for item in results]
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DMDL command line interface")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file")
    parser.add_argument(
        "--result",
        default="download_results.json",
        help="Where to store the JSON execution summary",
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
    payload = asyncio.run(run_from_config(Path(args.config), Path(args.result)))

    for index, item in enumerate(payload, start=1):
        status = "OK" if item["success"] else "FAIL"
        print(f"[{index}/{len(payload)}] {status} :: {item['source_url']}")
        if item["success"]:
            print(f"  saved_path: {item['saved_path']}")
        else:
            print(f"  error: {item['error']}")

    print(f"\nSaved summary -> {args.result}")


if __name__ == "__main__":
    main()
