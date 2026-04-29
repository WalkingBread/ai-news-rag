from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI

from app.settings import (
    EMBEDDING_MODEL,
    LANGUAGE_MODEL,
    OPEN_AI_API_KEY,
    OPEN_AI_API_URL,
    AZURE_API_VERSION,
    VECTOR_DIMENSIONS
)

class ModelProviderService:
    def __init__(self, embedding_model: str = EMBEDDING_MODEL, 
                 language_model: str = LANGUAGE_MODEL):   
        self._embedding_model = embedding_model
        self._language_model = language_model    

        self._embeddings = AzureOpenAIEmbeddings(
            model=self._embedding_model,
            openai_api_key=OPEN_AI_API_KEY,
            azure_endpoint=f'{OPEN_AI_API_URL}/{self._embedding_model}',
            dimensions=VECTOR_DIMENSIONS,
            api_version=AZURE_API_VERSION
        )

        self._llm = AzureChatOpenAI(
            model=self._language_model, 
            openai_api_key=OPEN_AI_API_KEY, 
            azure_endpoint=f'{OPEN_AI_API_URL}/{self._language_model}',
            api_version=AZURE_API_VERSION
        )

    @property
    def embedding_model(self) -> str:
        return self._embedding_model
    
    @property
    def language_model(self) -> str:
        return self._language_model
    
    @property
    def embeddings(self) -> AzureOpenAIEmbeddings:
        return self._embeddings
    
    @property
    def llm(self) -> AzureChatOpenAI:
        return self._llm