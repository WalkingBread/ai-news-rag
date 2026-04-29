from app.database.models import ProcessedSource, SourceChunk
from app.database import get_db_session

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from sqlalchemy import select

from app.services.search import VectorStorageService

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50

class ChunkingService:
    def __init__(self, storage_service: VectorStorageService, 
                 chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.storage_service = storage_service
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def chunk_sources(self):
        with get_db_session() as db:
            stmt = select(ProcessedSource).outerjoin(SourceChunk).where(SourceChunk.id == None)
            sources = db.execute(stmt).scalars().all()

        if not sources:
            return

        for source in sources:
            await self._chunk_source(source)


    async def _chunk_source(self, source: ProcessedSource):
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

        await self.storage_service.pg_store.aadd_documents(docs)

        await self.storage_service.os_store.aadd_texts(
            texts=[source.body],
            metadatas=[{
                "source_id": source.id, 
                "title": source.title,
                "url": source.url
            }],
            ids=[str(source.id)]
        )
