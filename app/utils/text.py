import re

def remove_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        u"["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002700-\U000027BF"
        u"\U0001F900-\U0001F9FF"
        u"]+", flags=re.UNICODE
    )

    return emoji_pattern.sub('', text)
