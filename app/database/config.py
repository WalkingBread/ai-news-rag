from alembic.config import Config
from app.settings import (
    DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
)

SYNC_CONN_PREFIX = 'postgresql'
ASYNC_CONN_PREFIX = 'postgresql+asyncpg'

CORE_DB_URL = f"{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}"
SYSTEM_DB_URL = f'{SYNC_CONN_PREFIX}://{CORE_DB_URL}/postgres'
RAG_DB_URL = f'{SYNC_CONN_PREFIX}://{CORE_DB_URL}/{DB_NAME}'
ASYNC_RAG_DB_URL = f'{ASYNC_CONN_PREFIX}://{CORE_DB_URL}/{DB_NAME}'


def get_alembic_config():
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f'{RAG_DB_URL}')
    return alembic_cfg