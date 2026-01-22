import os

from elasticsearch import AsyncElasticsearch
from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.stores.disk.store import DiskStore
from key_value.aio.stores.elasticsearch import ElasticsearchStore
from key_value.aio.stores.elasticsearch.store import ElasticsearchV1CollectionSanitizationStrategy


def get_elasticsearch_client() -> AsyncElasticsearch | None:
    if not (host := os.getenv("ES_URL")):
        return None

    if not (api_key := os.getenv("ES_API_KEY")):
        return None

    return AsyncElasticsearch(
        hosts=[host],
        api_key=api_key,
        http_compress=True,
        retry_on_timeout=True,
    )


def get_cache_backend() -> AsyncKeyValue:
    if elasticsearch_client := get_elasticsearch_client():
        return ElasticsearchStore(
            elasticsearch_client=elasticsearch_client,
            index_prefix="fastmcp-response-cache",
            collection_sanitization_strategy=ElasticsearchV1CollectionSanitizationStrategy(),
        )

    return DiskStore(directory=".store_data")
