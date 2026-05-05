from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from app.utils.logger import get_logger

from app.database.config import (
    RAG_DB_URL,
    SYSTEM_DB_URL,
    DB_NAME,
    get_alembic_config
)

logger = get_logger()

ENGINE = create_engine(
    RAG_DB_URL,
    echo=False,
    pool_size=10,  
    max_overflow=20
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=ENGINE,
    expire_on_commit=False
)

def setup_db():
    sys_engine = create_engine(SYSTEM_DB_URL, isolation_level="AUTOCOMMIT")

    with sys_engine.connect() as conn:
        exists = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")).scalar()
        
        if not exists:
            conn.execute(text(f"CREATE DATABASE {DB_NAME}"))

    sys_engine.dispose()
    
    logger.info("Running migrations...")
    command.upgrade(get_alembic_config(), "head")
    logger.info("Database is up to date.")

@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()