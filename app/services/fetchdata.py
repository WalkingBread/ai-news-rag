import feedparser
import time
import trafilatura
import anyio
import asyncio

from abc import abstractmethod
from app.database.models import RawSource
from app.database import get_db_session
from app.logger import get_logger

from datetime import datetime
from typing import AsyncGenerator

logger = get_logger('fetch_data_service')

RSS_SOURCES = {
    'Hugging Face': 'https://huggingface.co/blog/feed.xml',
    'OpenAI': 'https://openai.com/news/rss.xml',
    'MIT': 'https://www.technologyreview.com/topic/artificial-intelligence/feed/',
    'Deepmind': 'https://deepmind.google/blog/rss.xml'
}

# ARXIV = 'http://arxiv.org/rss/cs.AI'

class DataSource:
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def fetch_data(self) -> AsyncGenerator[RawSource, None]:
        pass

    def _create_row(self, url: str, title: str, 
                   body: str, published_at: datetime):
        return RawSource(
            source=self.name,
            url=url,
            title=title,
            body=body,
            published_at=published_at,
            created_at=datetime.now()
        )


class RSSDataSource(DataSource):
    def __init__(self, name):
        super().__init__(name)
        self.url = RSS_SOURCES[name]

    async def fetch_data(self, extract_interval=1) -> AsyncGenerator[RawSource, None]:
        feed = feedparser.parse(self.url)

        for entry in feed.entries:
            published_parsed = entry.get('published_parsed')
            published_dt = datetime.fromtimestamp(
                time.mktime(published_parsed)) if published_parsed else None
            
            url = entry.get('link')
            
            content = self._extract_content_from_rss(entry)

            if not content and url:
                content = await self._extract_content_from_url(url)
                await asyncio.sleep(extract_interval)

            if not content:
                continue

            yield self._create_row(
                url,
                entry.get('title'),
                content,
                published_dt
            )

    def _extract_content_from_rss(self, _entry) -> str:
        return None
    
    async def _extract_content_from_url(self, url):
        return await anyio.to_thread.run_sync(trafilatura.fetch_url, url)      
    

class HuggingFaceRSS(RSSDataSource):
    def __init__(self):
        super().__init__('Hugging Face')
    

class OpenAIRSS(RSSDataSource):
    def __init__(self):
        super().__init__('OpenAI')


class MITRSS(RSSDataSource):
    def __init__(self):
        super().__init__('MIT')

    def _extract_content_from_rss(self, entry):
        content = entry.get('content')
        return content[0].get('value') if content else None


class DeepmindRSS(RSSDataSource):
    def __init__(self):
        super().__init__('Deepmind')


class FetchDataService:
    def __init__(self):
        self.data_sources = [
            HuggingFaceRSS(),
            OpenAIRSS(),
            MITRSS(),
            DeepmindRSS()
        ]

    async def fetch_data(self):
        for data_source in self.data_sources:
            async for source in data_source.fetch_data():
                logger.info(f'Fetched data from {source.url}')
                with get_db_session() as db:
                    existing = db.query(RawSource).filter(RawSource.url == source.url).first()

                    if existing:
                        continue

                    db.add(source)
                    db.commit()