import asyncio

from dmdl.core.manager import DownloadManager
from dmdl.models.download_task import DownloadTask


class StubAdapter:
    name = 'stub'

    def can_handle(self, task: DownloadTask) -> bool:
        return True

    async def download(self, task: DownloadTask):
        await asyncio.sleep(0)
        return {
            'saved_path': 'downloads/file.pdf',
            'metadata': {
                'content_type': 'application/pdf',
                'title': 'file.pdf',
                'source_url': task.url,
            },
        }


def test_run_many_preserves_order() -> None:
    manager = DownloadManager(auto_load_plugins=False)
    manager.adapters = [StubAdapter()]
    tasks = [
        DownloadTask(url='https://example.com/1.pdf', requested_type='pdf'),
        DownloadTask(url='https://example.com/2.pdf', requested_type='pdf'),
    ]

    results = asyncio.run(manager.run_many(tasks, concurrency=2))
    assert [item.source_url for item in results] == [
        'https://example.com/1.pdf',
        'https://example.com/2.pdf',
    ]
    assert all(item.success for item in results)
    assert results[0].record is not None
    assert results[0].record.meta['_schema']['name'] == 'pdf'
