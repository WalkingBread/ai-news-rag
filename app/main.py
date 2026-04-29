import logging

from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy import select

from app.database.models import ProcessedSource
from app.database import setup_db, get_db_session
from app.services.fetchdata import FetchDataService
from app.services.rag import RAGService
from app.services.processdata import ProcessDataService
from app.services.modelprovider import ModelProviderService
from app.services.search import VectorStorageService
from app.services.chunk import ChunkingService
from app.services.query import QueryService


MODEL_PROVIDER_SERVICE = ModelProviderService()
VECTOR_STORAGE_SERVICE = VectorStorageService(MODEL_PROVIDER_SERVICE.embeddings)

FETCH_DATA_SERVICE = FetchDataService()
PROCESS_DATA_SERVICE = ProcessDataService()
CHUNKING_SERVICE = ChunkingService(VECTOR_STORAGE_SERVICE)

QUERY_SERVICE = QueryService(MODEL_PROVIDER_SERVICE, VECTOR_STORAGE_SERVICE)

RAG_SERVICE = RAGService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_db()

    await VECTOR_STORAGE_SERVICE.setup_opensearch_index()
    yield


app = FastAPI(lifespan=lifespan)


@app.get('/')
def root():
    with get_db_session() as db:
        sources = db.execute(select(ProcessedSource)).scalars().all()
    
    return sources

@app.get('/fetch')
async def fetch(background_tasks: BackgroundTasks):
    background_tasks.add_task(FETCH_DATA_SERVICE.fetch_data)

    return {'Data is being fetched...'}

@app.get('/process')
async def process(background_tasks: BackgroundTasks):
    background_tasks.add_task(PROCESS_DATA_SERVICE.process)

    return {'Data is being processed...'}

@app.get('/chunk')
async def chunk(background_tasks: BackgroundTasks):
    background_tasks.add_task(CHUNKING_SERVICE.chunk_sources)
    return {'Chunking commenced...'}

@app.get('/ask')
async def ask():
    try:
        response = await QUERY_SERVICE.query('Tell me something about recent models.')
    except Exception as e:
        import traceback
        traceback.print_exc()
    return response