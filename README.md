# DMDL

## Dlegoream Media Download Library

DMDL is a lightweight Python library for downloading media, extracting metadata, and converting external files into Dlegoream-friendly records.

## What improved in 1.1.1

- Runtime logging was split into a dedicated `dmdl.logging` package with structured message helpers
- Adapter discovery and registration were separated into `dmdl.plugins` with a reusable registry
- `DownloadManager` now delegates adapter resolution to `AdapterRegistry`
- External adapters can be loaded from import paths or Python entry points (`dmdl.adapters`)
- CLI now supports `--log-level` and config-based plugin loading
- Config can now be split into a `config/` folder so links can be added in JSON without touching code
- Output paths can now be routed automatically by `requested_type`, `adapter_hint`, or `path_key`
- Tests were expanded for registry selection, lifecycle logging, and config-folder loading

## Installation

```bash
pip install git+https://github.com/dlegoreamlab/dmdl.git
```

For local development:

```bash
pip install -e .
```

## Quick start

```python
import asyncio

from dmdl import Downloader


async def main() -> None:
    downloader = Downloader(
        download_dir="downloads",
        max_concurrency=3,
        quality="1080p",
        subtitle=True,
        subtitle_langs=["ko", "en"],
        subtitle_format="srt",
    )

    result = await downloader.download(
        url="https://youtube.com/watch?v=example",
        requested_type="youtube_video",
        quality="720p",
        subtitle_langs=["ko", "en", "ja"],
    )

    print(result.success)
    print(result.saved_path)
    print(result.metadata.get("title"))


asyncio.run(main())
```

## Plugin loading example

```python
import asyncio

from dmdl import Downloader


async def main() -> None:
    downloader = Downloader(download_dir="downloads", auto_load_plugins=False)
    downloader.load_plugins([
        "my_project.adapters:CustomAdapter",
    ])

    result = await downloader.download(
        url="https://example.com/file.pdf",
        requested_type="pdf",
        adapter_hint="custom-adapter",
    )
    print(result.to_dict())


asyncio.run(main())
```

## CLI usage

```bash
dmdl --config config --log-level DEBUG
```

You can still run the compatibility launcher:

```bash
python run.py
```

## Configuration example

`config/settings.json`

```json
{
  "defaults": {
    "quality": "1080p",
    "subtitle": true,
    "subtitle_langs": ["ko", "en"],
    "subtitle_format": "best",
    "merge_output_format": "mp4",
    "thumbnail": true,
    "playlist": false,
    "node_id": "local",
    "max_concurrency": 3,
    "auto_load_plugins": true
  },
  "paths": {
    "download_dir": "downloads",
    "results_file": "download_results.json",
    "by_requested_type": {
      "youtube_video": "downloads/youtube",
      "video": "downloads/video",
      "pdf": "downloads/docs"
    },
    "by_adapter_hint": {
      "telegram": "downloads/telegram"
    },
    "named": {
      "private_room": "downloads/telegram/private_room"
    }
  },
  "include": ["links.json"]
}
```

`config/links.json`

```json
{
  "targets": [
    {
      "url": "https://youtube.com/watch?v=example",
      "requested_type": "youtube_video",
      "quality": "720p",
      "subtitle_langs": ["ko", "en"],
      "subtitle_format": "srt"
    },
    {
      "url": "https://example.com/sample.pdf",
      "requested_type": "pdf"
    },
    {
      "url": "https://t.me/c/1234567890/42",
      "requested_type": "video",
      "adapter_hint": "telegram",
      "path_key": "private_room"
    }
  ]
}
```

링크 추가는 `config/links.json` 또는 `config/links/*.json`에만 넣으면 됩니다. 코드 수정 없이 자동으로 읽습니다.

## Package structure

```text
DMDL
├── dmdl
│   ├── adapters
│   ├── core
│   ├── events
│   ├── logging
│   ├── models
│   ├── plugins
│   └── utils
├── tests
├── config
│   ├── links.json.example
│   └── settings.json.example
├── config.json.example
├── pyproject.toml
└── run.py
```

## Notes

- `Downloader.download()` and `Downloader.download_many()` are asynchronous
- `requested_type` must be one of: `article`, `image`, `music`, `pdf`, `video`, `youtube_video`
- Direct file downloads support custom request headers through `options.headers`
- Duplicate filenames are automatically renamed with numeric suffixes
- 코드에서는 `Downloader(...)` 기본값이나 `download(..., quality="720p", subtitle_langs=[...])`처럼 호출별 옵션으로 화질/자막을 바로 제어할 수 있습니다
- 설정 파일에서는 `quality`, `subtitle`, `subtitle_langs`, `subtitle_format`, `format_selector`, `merge_output_format`를 타깃별로 지정할 수 있습니다
- `config/` 폴더를 넘기면 `settings.json`, `links.json`, `links/*.json`, `targets/*.json`를 자동으로 병합합니다
- 대상별 저장 경로는 `paths.by_requested_type`, `paths.by_adapter_hint`, `paths.named`로 분리할 수 있습니다
- Plugin entry points should use the `dmdl.adapters` group

## Telegram / Telethon support

DMDL now includes a built-in `TelegramAdapter` based on Telethon.

### Supported target forms

- `https://t.me/<username>/<message_id>`
- `https://t.me/c/<internal_chat_id>/<message_id>` for private supergroups/channels that the authenticated account can already access
- `https://t.me/<username>` + `telegram_message_ids` or `telegram_from_message_id` / `telegram_to_message_id`

### Important safety / scope note

- This adapter only works with the Telegram account or bot session you provide.
- It does **not** bypass Telegram permissions.
- Private chat downloads are only possible when the authenticated session already has legitimate access.
- FloodWait is respected by default through automatic backoff (`telegram_max_flood_wait`, `telegram_wait_buffer`, `telegram_retry_limit`).

### Example config

```json
{
  "defaults": {
    "download_dir": "downloads",
    "max_concurrency": 1,
    "auto_load_plugins": true
  },
  "targets": [
    {
      "url": "https://t.me/c/1234567890/42",
      "requested_type": "video",
      "adapter_hint": "telegram",
      "output_dir": "downloads/telegram/private_room",
      "options": {
        "telegram_api_id": "123456",
        "telegram_api_hash": "YOUR_API_HASH",
        "telegram_session": "dmdl_telegram",
        "telegram_max_flood_wait": 300,
        "telegram_wait_buffer": 3,
        "telegram_per_file_delay": 1.5
      }
    }
  ]
}
```

### Auth note

For user-account downloads, prepare a logged-in Telethon session file or session string first. A session string can also be supplied with `telegram_session_string` or the `DMDL_TELEGRAM_SESSION_STRING` environment variable.

## License

Apache License 2.0
