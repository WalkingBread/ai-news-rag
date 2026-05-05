from app.database import get_db_session
from app.database.models import RawSource, ProcessedSource

from app.utils.text import remove_emojis

from sqlalchemy import select

import trafilatura
import re

class ProcessDataService:
    def __init__(self):
        pass

    def _clean_content(self, text: str) -> str:
        text = remove_emojis(text)

        noise_patterns = [
            r'(Share this:|Follow us on|Click to copy).*',
            r'(Subscribe to our newsletter|Join our mailing list).*',
            r'Read more\s*»',
            r'Privacy Policy|Terms of Service',
        ]

        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        text = re.sub(r'\t+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()

    def _preprocess_content(self, body) -> str:
        content = trafilatura.extract(
            body,
            output_format="markdown", 
            include_comments=False,
            include_tables=True,
            include_links=False
        )

        return self._clean_content(content)

    def _process_source(self, row: RawSource) -> ProcessedSource:
        return ProcessedSource(
            raw_source_id=row.id,
            source=row.source,
            url=row.url,
            title=row.title,
            body=self._preprocess_content(row.body),
            published_at=row.published_at
        )
    
    def process(self):
        with get_db_session() as db:
            query = select(RawSource).outerjoin(ProcessedSource).where(ProcessedSource.id == None)
            rows = db.execute(query).scalars().all()

        for row in rows:
            with get_db_session() as db:
                processed_source = self._process_source(row)

                db.add(processed_source)
                db.commit()