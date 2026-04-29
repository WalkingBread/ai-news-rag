import os
from dotenv import load_dotenv

load_dotenv()

VECTOR_DIMENSIONS = 1536

EMBEDDING_MODEL = 'text-embedding-3-small'
LANGUAGE_MODEL = 'gpt-4o'

AZURE_API_VERSION = '2024-10-21'

DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')
OPEN_AI_API_URL = os.getenv('OPEN_AI_API_URL')

OPENSEARCH_URL = os.getenv('OPENSEARCH_URL')
OPENSEARCH_INDEX = os.getenv('OPENSEARCH_INDEX')

OS_HYBRID_SEARCH_PIPELINE = "hybrid-search-pipeline"

OPENSEARCH_INDEX_BODY = {
    "settings": {
        "index.knn": True,
        "index.knn.algo_param.ef_search": 100,
        "index.search.default_pipeline": OS_HYBRID_SEARCH_PIPELINE
    },
    "mappings": {
        "properties": {
            "vector_field": {
                "type": "knn_vector",
                "dimension": VECTOR_DIMENSIONS,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "lucene",
                    "parameters": {
                        "m": 16,
                        "ef_construction": 128
                    }
                }
            },
            "text": { "type": "text" },
            "source_id": { "type": "keyword" },
            "title": { "type": "text" }
        }
    }
}

OS_HYBRID_SEARCH_PIPELINE_BODY = {
    "description": "Post-processor for hybrid search",
    "phase_results_processors": [
        {
            "normalization-processor": {
                "normalization": {"technique": "min_max"},
                "combination": {
                    "technique": "arithmetic_mean",
                    "parameters": {"weights": [0.3, 0.7]} # 30% BM25, 70% Vector
                }
            }
        }
    ]
}