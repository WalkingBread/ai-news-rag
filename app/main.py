import logging

from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy import select

from app.database.models import ProcessedSource
from app.database import setup_db, get_db_session
from app.services.fetchdata import FetchDataService
from app.services.rag import RAGService
from app.services.processdata import ProcessDataService

FETCH_DATA_SERVICE = FetchDataService()
PROCESS_DATA_SERVICE = ProcessDataService()
RAG_SERVICE = RAGService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_db()

    await RAG_SERVICE.setup_opensearch_index()
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
    background_tasks.add_task(RAG_SERVICE.chunk_sources)
    return {'Chunking commenced...'}