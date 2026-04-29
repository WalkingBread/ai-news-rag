import os
from dotenv import load_dotenv

load_dotenv()

VECTOR_DIMENSIONS = 1536

DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')
OPEN_AI_API_URL = os.getenv('OPEN_AI_API_URL')

OPENSEARCH_URL = os.getenv('OPENSEARCH_URL')
OPENSEARCH_INDEX = os.getenv('OPENSEARCH_INDEX')

OPENSEARCH_INDEX_BODY = {
    "settings": {
        "index.knn": True,
        "index.knn.algo_param.ef_search": 100
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
            "source_id": { "type": "keyword" },
            "title": { "type": "text" }
        }
    }
}