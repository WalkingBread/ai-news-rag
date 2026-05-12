from app.services.modelprovider import ModelProviderService
from app.services.search import VectorStorageService

from app.settings import OS_SEARCH_PARAMS

from langfuse import observe, get_client
from langfuse.langchain import CallbackHandler

class QueryService:
    def __init__(self, model_provider: ModelProviderService, 
                 storage_service: VectorStorageService):
        self.model_provider = model_provider
        self.storage_service = storage_service

        self.langfuse = get_client()

    @observe(name="ai_news_query")
    async def query(self, question: str) -> str:
        langfuse_handler = CallbackHandler()

        scout_results = await self.storage_service.os_store.asimilarity_search(
            question, 
            k=3,
            callbacks=[langfuse_handler],
            **OS_SEARCH_PARAMS
        )
        
        if not scout_results:
            return "I couldn't find any relevant news."

        target_ids = [doc.metadata["source_id"] for doc in scout_results]

        chunks = await self.storage_service.pg_store.asimilarity_search(
            question,
            k=5,
            filter={"source_id": {"$in": target_ids}},
            callbacks=[langfuse_handler]
        )

        context = "\n\n".join([c.page_content for c in chunks])

        prompt = f"""Use the following context to answer the question.
        Context:
        {context}

        Question: {question}
        Answer:"""

        response = await self.model_provider.llm.ainvoke(
            prompt,
            config={"callbacks": [langfuse_handler]}
        )

        return response.content
