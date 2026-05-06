from app.services.modelprovider import ModelProviderService

from app.database import get_db_session
from app.database.models import RefinedSource

from app.utils.token import get_token_count, truncate_to_tokens
from app.utils.logger import get_logger

from sqlalchemy import select
from typing import List
from pydantic import BaseModel, Field

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

logger = get_logger('summarization_service')

class SourceSummary(BaseModel):
    source_id: int = Field(description="The unique database ID of the article.")
    summary: str = Field(description="A one-sentence objective summary.")
    topics: List[str] = Field(description="A list of 3-5 relevant technical tags.")

class SummarizationResponse(BaseModel):
    items: List[SourceSummary]


MAX_BATCH_TOKENS = 5000
MAX_DOC_TOKENS = 1500

class SummarizationService:
    def __init__(self, model_provider: ModelProviderService,
                 max_batch_tokens=MAX_BATCH_TOKENS, max_doc_tokens=MAX_DOC_TOKENS):
        self.model_provider = model_provider
        self.max_batch_tokens = max_batch_tokens
        self.max_doc_tokens = max_doc_tokens

        self.parser = PydanticOutputParser(pydantic_object=SummarizationResponse)

    async def summarize_sources(self):
        with get_db_session() as db:
            stmt = select(RefinedSource).where(
                (RefinedSource.summary == None) | (RefinedSource.topics == None)
            )

            sources = db.execute(stmt).scalars().all()
        
            if not sources:
                return

            source_map = {s.id: s for s in sources}
            for batch in self._get_document_batches(sources):
                ids_str =  ", ".join(str(s[0]) for s in batch)
                logger.info(f'Summarizing sources: {ids_str}')
                response = await self._process_batch(batch)
                
                for item in response.items:
                    source = source_map.get(item.source_id)
                    source.summary = item.summary
                    source.topics = item.topics
                    db.commit()
                    logger.info(f'Summarization completed for source: {source.id}')


    async def _process_batch(self, batch) -> SummarizationResponse:
        formatted_articles = ""
        for item in batch:
            source_id, content = item
            formatted_articles += f"--- ARTICLE ID: {source_id} ---\n{content}\n"

        prompt = ChatPromptTemplate.from_template(
            "You are a technical analyst. Summarize the following articles and extract topics.\n"
            "CRITICAL: Map each summary to the correct ARTICLE ID provided.\n"
            "{format_instructions}\n"
            "Articles:\n{articles}"
        )

        chain = prompt | self.model_provider.llm | self.parser
        
        return await chain.ainvoke({
            "articles": formatted_articles,
            "format_instructions": self.parser.get_format_instructions()
        })
            
        
    def _get_document_batches(self, sources: List[RefinedSource]):
        current_batch = []
        used_tokens = 0

        for source in sources:
            content = source.body
            source_tokens = get_token_count(content)

            if source_tokens > self.max_doc_tokens:
                source_tokens = self.max_doc_tokens
                content = truncate_to_tokens(source.body, self.max_doc_tokens)

            item = (source.id, content)

            if used_tokens + source_tokens > self.max_batch_tokens:
                yield current_batch
                current_batch = [item]
                used_tokens = source_tokens
            else:
                current_batch.append(item)
                used_tokens += source_tokens

        if current_batch:
            yield current_batch