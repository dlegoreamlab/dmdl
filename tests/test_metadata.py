from dmdl.core.metadata import MetadataManager


def test_metadata_manager_filters_unknown_keys() -> None:
    manager = MetadataManager(node_id='node-a')
    record = manager.build_record(
        source_url='https://example.com/a.pdf',
        path='downloads/a.pdf',
        record_type='pdf',
        meta={
            'title': 'A',
            'source_url': 'https://example.com/a.pdf',
            'page_count': 3,
            'ignored': 'x',
        },
    )
    assert record.meta == {
        'title': 'A',
        'source_url': 'https://example.com/a.pdf',
        'page_count': 3,
    }
    assert record.node_id == 'node-a'
