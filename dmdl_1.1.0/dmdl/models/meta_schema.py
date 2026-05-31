META_SCHEMA = {

    # =====================================================
    # MUSIC
    # =====================================================

    "music": {

        "fields": [

            "title",

            "artist",

            "album",

            "genre",

            "duration",

            "play_score"
        ],

        "semantic": [

            "topics",

            "keywords",

            "summary",

            "embedding"
        ]
    },

    # =====================================================
    # YOUTUBE VIDEO
    # =====================================================

    "youtube_video": {

        "fields": [

            "video_id",

            "title",

            "channel_id",

            "channel_title",

            "published_at",

            "duration",

            "view_count",

            "like_count",

            "comment_count",

            "category_id",

            "default_language",

            "thumbnail_url"
        ],

        "content": [

            "description",

            "tags",

            "transcript"
        ],

        "storage": [

            "downloaded",

            "audio_path",

            "subtitle_path",

            "video_size",

            "audio_size"
        ],

        "semantic": [

            "topics",

            "entities",

            "keywords",

            "summary",

            "embedding"
        ],

        "scoring": [

            "relevance",

            "freshness",

            "importance",

            "popularity_score"
        ],

        "relation": [

            "related_videos",

            "playlist_id",

            "series",

            "video_record_id"
        ]
    },

    # =====================================================
    # PDF
    # =====================================================

    "pdf": {

        "fields": [

            "title",

            "source_url",

            "page_count",

            "language"
        ],

        "content": [

            "snippet",

            "full_text"
        ],

        "semantic": [

            "topics",

            "entities",

            "keywords",

            "summary",

            "embedding"
        ],

        "scoring": [

            "relevance",

            "freshness"
        ]
    },

    # =====================================================
    # ARTICLE
    # =====================================================

    "article": {

        "fields": [

            "title",

            "source_url",

            "domain",

            "author",

            "published_at",

            "language"
        ],

        "content": [

            "snippet",

            "full_text",

            "blocks",

            "image_count",

            "heading_count",

            "paragraph_count"
        ],

        "semantic": [

            "semantic_type",

            "topics",

            "entities",

            "keywords",

            "summary",

            "embedding"
        ],

        "scoring": [

            "relevance",

            "freshness",

            "importance"
        ],

        "relation": [

            "related_articles",

            "source_cluster",

            "canonical_url"
        ]
    },

    # =====================================================
    # VIDEO (실제 영상 파일)
    # =====================================================

    "video": {

        "fields": [

            "title",

            "duration",

            "width",

            "height",

            "fps",

            "codec",

            "size",

            "source_type"
        ],

        "content": [

            "transcript"
        ],

        "semantic": [

            "topics",

            "objects",

            "entities",

            "summary",

            "embedding"
        ],

        "scoring": [

            "importance"
        ],

        "relation": [

            "source_record"
        ]
    },

    # =====================================================
    # IMAGE
    # =====================================================

    "image": {

        "fields": [

            "width",

            "height",

            "format",

            "camera"
        ],

        "gps": [

            "lat",

            "lon",

            "alt"
        ],

        "feature": [

            "scene",

            "objects",

            "dominant_color",

            "embedding"
        ],

        "map": [

            "tile",

            "geohash",

            "region"
        ]
    }
}