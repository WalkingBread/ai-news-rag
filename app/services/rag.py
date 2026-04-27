from app.database.models import ProcessedSource, SourceChunk
from app.database import get_db_session
from app.database.config import RAG_DB_URL
from app.settings import (
    OPEN_AI_API_KEY, 
    OPEN_AI_API_URL, 
    OPENSEARCH_URL, 
    OPENSEARCH_INDEX, 
    OPENSEARCH_INDEX_BODY, 
    VECTOR_DIMENSIONS
)

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import OpenSearchVectorSearch, PGVector
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from sqlalchemy import select

EMBEDDING_MODEL = "text-embedding-3-large"

class RAGService:
    def __init__(self, model: str = EMBEDDING_MODEL):   
        self.model = model     

        self.embeddings = OpenAIEmbeddings(
            model=self.model,
            openai_api_key=OPEN_AI_API_KEY,
            openai_proxy=OPEN_AI_API_URL,
            dimensions=VECTOR_DIMENSIONS
        )

        self.llm = ChatOpenAI(
            model="gpt-4o", 
            openai_api_key=OPEN_AI_API_KEY, 
            openai_proxy=OPEN_AI_API_URL
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
            #http_auth=("admin", "admin"),
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
            print('chunking source')
            try:
                await self._chunk_source(source)
            except Exception as e:
                print(str(e))


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

        print('a')
        await self.pg_store.aadd_documents(docs)

        print('b')
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
            k=2,
        )
        
        if not scout_results:
            return "I couldn't find any relevant news."

        target_ids = [doc.metadata["source_id"] for doc in scout_results]

        chunks = await self.pg_store.asimilarity_search(
            question,
            k=5,
            filter={"source_id": {"in": target_ids}}
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
        exists = self.os_store.client.indices.exists(index=OPENSEARCH_INDEX)
        if not exists:
            await self.os_store.client.indices.create(
                index=OPENSEARCH_INDEX,
                body=OPENSEARCH_INDEX_BODY
            )
        print('Opensearch Index is set up.')