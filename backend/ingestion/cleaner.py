import re
def clean_text(text:str)->str:
    text=re.sub(r'\n{3,}', '\n\n', text)
    text=re.sub(r'\s+', ' ', text)
    return text.strip()
