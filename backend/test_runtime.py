import os
from dotenv import load_dotenv
load_dotenv()
from app.config import settings

print("Runtime LLM_MODEL:", settings.LLM_MODEL)
print("Runtime EMBEDDING_MODEL:", settings.EMBEDDING_MODEL)
print("ENV LLM_MODEL:", os.getenv("LLM_MODEL"))
print("ENV EMBEDDING_MODEL:", os.getenv("EMBEDDING_MODEL"))
