from app.database import get_db_session
from app.database.models import RawSource, ProcessedSource, RefinedSource
from app.database.types import SignedInt64

from app.utils.text import remove_emojis, hash, simhash

from sqlalchemy import select, text, bindparam
from sqlalchemy.orm import Session

from urllib.parse import urlparse, urlunparse

import trafilatura
import re


SIMHASH_THRESHOLD = 3

class ProcessDataService:
    def __init__(self, simhash_threshold: int = SIMHASH_THRESHOLD):
        self.simhash_threshold = simhash_threshold

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
    
    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    def _process_source(self, row: RawSource) -> ProcessedSource:
        processed_body = self._preprocess_content(row.body)
        
        return ProcessedSource(
            raw_source_id=row.id,
            source=row.source,
            url=self._normalize_url(row.url),
            title=remove_emojis(row.title),
            body=processed_body,
            published_at=row.published_at,
            content_hash=hash(processed_body),
            simhash=simhash(processed_body)
        )
    
    def _is_duplicate(self, row: ProcessedSource, db: Session):
        normalized_url = self._normalize_url(row.url)
        url_stmt = select(ProcessedSource.id).where(
            ProcessedSource.url == normalized_url,
            ProcessedSource.id != row.id
        )
        if db.execute(url_stmt).fetchone():
            return True

        exact_stmt = select(ProcessedSource.id).where(
            ProcessedSource.content_hash == row.content_hash,
            ProcessedSource.id != row.id
        )
        if db.execute(exact_stmt).fetchone():
            return True

        fuzzy_stmt = text("""
            SELECT id FROM source 
            WHERE id != :current_id 
                AND length(replace((simhash # :f_hash)::bit(64)::text, '0', '')) <= :limit
            LIMIT 1
        """).bindparams(
            bindparam("f_hash", type_=SignedInt64)
        )
        fuzzy_check = db.execute(fuzzy_stmt, {
            "f_hash": row.simhash, 
            "limit": self.simhash_threshold,
            "current_id": row.id
        }).fetchone()
        
        return fuzzy_check is not None
        
    
    def _refine_source(self, row: ProcessedSource) -> RefinedSource:
        return RefinedSource(
            processed_source_id=row.id,
            source=row.source,
            url=row.url,
            title=row.title,
            body=row.body,
            published_at=row.published_at,
            authority_score=1.0,
            momentum_score=1.0
        )
    
    def process(self):
        with get_db_session() as db:
            query = select(RawSource).outerjoin(ProcessedSource).where(ProcessedSource.id == None)
            rows = db.execute(query).scalars().all()

        for row in rows:
            with get_db_session() as db:
                processed_source = self._process_source(row)
                db.add(processed_source)
                db.flush()

                if not self._is_duplicate(processed_source, db):
                    refined_source = self._refine_source(processed_source)
                    db.add(refined_source)

                db.commit()