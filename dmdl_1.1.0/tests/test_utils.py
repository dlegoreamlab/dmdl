from pathlib import Path

from dmdl.models.download_task import DownloadTask
from dmdl.utils.filename import guess_filename_from_headers, sanitize_filename
from dmdl.utils.path import build_output_path, ensure_unique_path


def test_sanitize_filename_removes_invalid_chars() -> None:
    assert sanitize_filename(' a:/bad*name?.mp4 ') == 'a__bad_name_.mp4'


def test_guess_filename_from_headers_supports_rfc5987() -> None:
    header = "attachment; filename*=UTF-8''%ED%95%9C%EA%B8%80.mp4"
    assert guess_filename_from_headers(header) == '한글.mp4'


def test_ensure_unique_path_appends_suffix(tmp_path: Path) -> None:
    original = tmp_path / 'file.txt'
    original.write_text('x', encoding='utf-8')
    unique = ensure_unique_path(original)
    assert unique.name == 'file_1.txt'


def test_build_output_path_creates_directory(tmp_path: Path) -> None:
    path = build_output_path(tmp_path / 'nested', 'video.mp4')
    assert path.parent.exists()
    assert path.name == 'video.mp4'


def test_download_task_validates_url() -> None:
    task = DownloadTask(url='https://example.com/a.pdf', requested_type='pdf')
    assert task.output_dir == 'downloads'
    assert task.url == 'https://example.com/a.pdf'
