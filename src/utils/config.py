# src/utils/config.py
from pydantic import BaseModel
from dotenv import load_dotenv
import os
load_dotenv()

class Settings(BaseModel):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    kraken_key: str = os.getenv("KRAKEN_API_KEY", "")
    kraken_secret: str = os.getenv("KRAKEN_API_SECRET", "")

settings = Settings()