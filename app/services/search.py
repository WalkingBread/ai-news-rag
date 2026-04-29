from langchain_community.vectorstores import OpenSearchVectorSearch, PGVector

from app.database.config import RAG_DB_URL
from app.settings import (
    OPENSEARCH_URL,
    OPENSEARCH_INDEX,
    OPENSEARCH_INDEX_BODY,
    OS_HYBRID_SEARCH_PIPELINE,
    OS_HYBRID_SEARCH_PIPELINE_BODY
)

class VectorStorageService:
    def __init__(self, embeddings):
        self.pg_store = PGVector(
            connection_string=RAG_DB_URL,
            embedding_function=embeddings,
            collection_name="source_chunk",
            use_jsonb=True
        )
        
        self.os_store = OpenSearchVectorSearch(
            opensearch_url=OPENSEARCH_URL,
            index_name=OPENSEARCH_INDEX,
            embedding_function=embeddings,
            use_ssl=False,
            verify_certs=False
        )

    async def setup_opensearch_index(self):
        self.os_store.client.search_pipeline.put(
            id=OS_HYBRID_SEARCH_PIPELINE, 
            body=OS_HYBRID_SEARCH_PIPELINE_BODY
        )

        exists = self.os_store.client.indices.exists(index=OPENSEARCH_INDEX)
        if not exists:
            await self.os_store.client.indices.create(
                index=OPENSEARCH_INDEX,
                body=OPENSEARCH_INDEX_BODY
            )

        print('Opensearch Index is set up.')