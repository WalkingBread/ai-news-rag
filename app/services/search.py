from app.database.models import RefinedSource
from app.database import get_db_session
from app.utils.logger import get_logger

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import OpenSearchVectorSearch, PGVector

from sqlalchemy import select

from app.database.config import RAG_DB_URL
from app.settings import (
    OPENSEARCH_URL,
    OPENSEARCH_INDEX,
    OPENSEARCH_INDEX_BODY,
    OS_HYBRID_SEARCH_PIPELINE,
    OS_HYBRID_SEARCH_PIPELINE_BODY
)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50

logger = get_logger('vector_storage')

main_logger = get_logger()

class VectorStorageService:
    def __init__(self, embeddings, chunk_size: int = CHUNK_SIZE, 
                 chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

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
            verify_certs=False,
        )

    async def process_sources(self):
        with get_db_session() as db:
            stmt = select(RefinedSource).where(RefinedSource.vectorized == False)
            sources = db.execute(stmt).scalars().all()

            if not sources:
                return

            for source in sources:
                await self._chunk_source(source)
                await self._index_source(source)
    
                source.vectorized = True
                db.commit()


    async def _chunk_source(self, source: RefinedSource):
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )
        texts = splitter.split_text(source.body)
        
        docs = [
            Document(
                page_content=t, 
                metadata={"source_id": source.id, "title": source.title}
            ) for t in texts
        ]

        await self.pg_store.aadd_documents(docs)

    async def _index_source(self, source: RefinedSource):
        topics = source.topics if source.topics else []

        await self.os_store.aadd_texts(
            texts=[source.body],
            metadatas=[{
                "source_id": source.id, 
                "title": source.title,
                "url": source.url,
                "summary": source.summary,
                "topics": topics,
                "authority_score": source.authority_score,
                "momentum_score": source.momentum_score,
                "published_at": source.published_at.isoformat()
            }],
            ids=[str(source.id)]
        )


    def setup_opensearch_index(self):
        self.os_store.client.search_pipeline.put(
            id=OS_HYBRID_SEARCH_PIPELINE, 
            body=OS_HYBRID_SEARCH_PIPELINE_BODY
        )

        exists = self.os_store.client.indices.exists(index=OPENSEARCH_INDEX)
        if not exists:
            self.os_store.client.indices.create(
                index=OPENSEARCH_INDEX,
                body=OPENSEARCH_INDEX_BODY
            )
        main_logger.info('OpenSearch index is set up.')