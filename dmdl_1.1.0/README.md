# DMDL

## Dlegoream Media Download Library

DMDL is a lightweight Python library for downloading media, extracting metadata, and converting external files into Dlegoream-friendly records.

## What improved in 1.1.0

- Runtime logging was split into a dedicated `dmdl.logging` package with structured message helpers
- Adapter discovery and registration were separated into `dmdl.plugins` with a reusable registry
- `DownloadManager` now delegates adapter resolution to `AdapterRegistry`
- External adapters can be loaded from import paths or Python entry points (`dmdl.adapters`)
- CLI now supports `--log-level` and config-based plugin loading
- Tests were expanded for registry selection and lifecycle logging

## Installation

```bash
pip install dmdl
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
    downloader = Downloader(download_dir="downloads", max_concurrency=3)

    result = await downloader.download(
        url="https://youtube.com/watch?v=example",
        requested_type="youtube_video",
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
dmdl --config config.json --result download_results.json --log-level DEBUG
```

You can still run the compatibility launcher:

```bash
python run.py
```

## Configuration example

```json
{
  "defaults": {
    "quality": "1080p",
    "subtitle": true,
    "thumbnail": true,
    "playlist": false,
    "download_dir": "downloads",
    "node_id": "local",
    "max_concurrency": 3,
    "auto_load_plugins": true
  },
  "plugins": [
    "my_project.adapters:CustomAdapter"
  ],
  "targets": [
    {
      "url": "https://youtube.com/watch?v=example",
      "requested_type": "youtube_video"
    },
    {
      "url": "https://example.com/sample.pdf",
      "requested_type": "pdf",
      "output_dir": "downloads/docs",
      "options": {
        "timeout": 120
      }
    }
  ]
}
```

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
├── config.json.example
├── pyproject.toml
└── run.py
```

## Notes

- `Downloader.download()` and `Downloader.download_many()` are asynchronous
- `requested_type` must be one of: `article`, `image`, `music`, `pdf`, `video`, `youtube_video`
- Direct file downloads support custom request headers through `options.headers`
- Duplicate filenames are automatically renamed with numeric suffixes
- Plugin entry points should use the `dmdl.adapters` group

## License

Apache License 2.0
