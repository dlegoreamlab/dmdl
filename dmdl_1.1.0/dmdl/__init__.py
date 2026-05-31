from .core.downloader import Downloader
from .core.manager import DownloadManager
from .logging import StructuredLogger, configure_logging, get_logger
from .models.download_result import DownloadResult
from .models.download_task import DownloadTask
from .models.meta_schema import META_SCHEMA
from .models.schema import FileRecord
from .plugins import AdapterRegistry

__version__ = "1.1.0"

__all__ = [
    "Downloader",
    "DownloadManager",
    "DownloadTask",
    "DownloadResult",
    "FileRecord",
    "META_SCHEMA",
    "AdapterRegistry",
    "StructuredLogger",
    "configure_logging",
    "get_logger",
    "__version__",
]
