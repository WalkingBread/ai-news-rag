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

SOURCE_AUTHORITY = {
    'Hugging Face': 1.0
}

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
            authority_score = self._calculate_authority(row.source),
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
        
    def _calculate_authority(self, source_name: str):
        return SOURCE_AUTHORITY.get(source_name, 1.0)
    
    def _calculate_momentum(self):
        pass
    
    def _refine_source(self, row: ProcessedSource, momentum: float) -> RefinedSource:
        return RefinedSource(
            processed_source_id=row.id,
            source=row.source,
            url=row.url,
            title=row.title,
            body=row.body,
            published_at=row.published_at,
            momentum_score=momentum,
            authority_score=row.authority_score
        )
    
    def process(self):
        with get_db_session() as db:
            query = select(RawSource).outerjoin(ProcessedSource).where(ProcessedSource.id == None)
            rows = db.execute(query).scalars().all()

        if not rows:
            return

        for row in rows:
            with get_db_session() as db:
                processed_source = self._process_source(row)
                db.add(processed_source)
                db.commit()

    def _get_cluster_ids(self, row: ProcessedSource, db: Session) -> list[int]:
        fuzzy_stmt = text("""
            SELECT id FROM source 
            WHERE length(replace((simhash # :f_hash)::bit(64)::text, '0', '')) <= :limit
        """).bindparams(bindparam("f_hash", type_=SignedInt64))
        
        results = db.execute(fuzzy_stmt, {
            "f_hash": row.simhash, 
            "limit": self.simhash_threshold
        }).scalars().all()

        return results

    def refine(self):
        with get_db_session() as db:
            query = (
                select(ProcessedSource)
                .outerjoin(RefinedSource)
                .where(RefinedSource.id == None)
                .order_by(
                    ProcessedSource.authority_score.desc(), 
                    ProcessedSource.published_at.desc()
                )
            )
            rows = db.execute(query).scalars().all()

            if not rows:
                return
            
            for row in rows:
                cluster_ids = self._get_cluster_ids(row, db)

                gold_stmt = select(RefinedSource.id).where(
                    RefinedSource.processed_source_id.in_(cluster_ids)
                )

                if db.execute(gold_stmt).fetchone():
                    continue
                
                momentum = self._calculate_momentum(len(cluster_ids), row.published_at)

                refined_source = self._refine_source(row, momentum)
                
                db.add(refined_source)
                db.commit()