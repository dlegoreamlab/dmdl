from dmdl.core.metadata import MetadataManager


def test_metadata_manager_normalizes_to_dfss_sections() -> None:
    manager = MetadataManager(node_id='node-a')
    record = manager.build_record(
        source_url='https://example.com/a.pdf',
        path='downloads/a.pdf',
        record_type='pdf',
        meta={
            'title': 'A',
            'source_url': 'https://example.com/a.pdf',
            'page_count': 3,
            'content_type': 'application/pdf',
            'size': 42,
            'ignored': 'x',
        },
    )
    assert record.meta == {
        '_schema': {'name': 'pdf', 'version': '1.0'},
        'fields': {
            'title': 'A',
            'source_url': 'https://example.com/a.pdf',
            'page_count': 3,
            'mime_type': 'application/pdf',
            'size': 42,
            'file_name': 'a.pdf',
        },
    }
    assert record.node_id == 'node-a'
    assert record.validate() is True
