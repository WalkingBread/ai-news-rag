import tiktoken

from app.settings import LANGUAGE_MODEL

def get_token_count(text: str, model=LANGUAGE_MODEL):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def truncate_to_tokens(text: str, max_tokens: int, model=LANGUAGE_MODEL):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return encoding.decode(tokens[:max_tokens])