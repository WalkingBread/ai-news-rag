from app.database.models import ProcessedSource, SourceChunk
from app.database import get_db_session
from app.database.config import RAG_DB_URL
from app.settings import (
    OPEN_AI_API_KEY, 
    OPEN_AI_API_URL, 
    OPENSEARCH_URL, 
    OPENSEARCH_INDEX, 
    OPENSEARCH_INDEX_BODY,
    OS_HYBRID_SEARCH_PIPELINE, 
    OS_HYBRID_SEARCH_PIPELINE_BODY,
    VECTOR_DIMENSIONS,
    EMBEDDING_MODEL,
    LANGUAGE_MODEL,
    AZURE_API_VERSION
)

from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_community.vectorstores import OpenSearchVectorSearch, PGVector
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from sqlalchemy import select

class RAGService:
    def __init__(self, embedding_model: str = EMBEDDING_MODEL, 
                 language_model: str = LANGUAGE_MODEL):   
        self.embed_model = embedding_model
        self.lang_model = language_model    

        self.embeddings = AzureOpenAIEmbeddings(
            model=self.embed_model,
            openai_api_key=OPEN_AI_API_KEY,
            azure_endpoint=f'{OPEN_AI_API_URL}/{self.embed_model}',
            dimensions=VECTOR_DIMENSIONS,
            api_version=AZURE_API_VERSION
        )

        self.llm = AzureChatOpenAI(
            model=self.lang_model, 
            openai_api_key=OPEN_AI_API_KEY, 
            azure_endpoint=f'{OPEN_AI_API_URL}/{self.lang_model}',
            api_version=AZURE_API_VERSION
        )

        self.pg_store = PGVector(
            connection_string=RAG_DB_URL,
            embedding_function=self.embeddings,
            collection_name="source_chunk",
            use_jsonb=True
        )
        
        self.os_store = OpenSearchVectorSearch(
            opensearch_url=OPENSEARCH_URL,
            index_name=OPENSEARCH_INDEX,
            embedding_function=self.embeddings,
            use_ssl=False,
            verify_certs=False
        )


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
            chunk_size=512, chunk_overlap=50
        )
        texts = splitter.split_text(source.body)
        
        docs = [
            Document(
                page_content=t, 
                metadata={"source_id": source.id, "title": source.title}
            ) for t in texts
        ]

        await self.pg_store.aadd_documents(docs)

        await self.os_store.aadd_texts(
            texts=[source.body],
            metadatas=[{
                "source_id": source.id, 
                "title": source.title,
                "url": source.url
            }],
            ids=[str(source.id)]
        )


    async def answer_question(self, question: str) -> str:
        scout_results = await self.os_store.asimilarity_search(
            question, 
            k=2
        )
        
        if not scout_results:
            return "I couldn't find any relevant news."

        target_ids = [doc.metadata["source_id"] for doc in scout_results]

        chunks = await self.pg_store.asimilarity_search(
            question,
            k=5,
            filter={"source_id": {"$in": target_ids}}
        )

        context = "\n\n".join([c.page_content for c in chunks])
        prompt = f"""Use the following context from the AI Radar to answer the question.
        Context:
        {context}

        Question: {question}
        Answer:"""

        response = await self.llm.ainvoke(prompt)
        return response.content
    

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