from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

    # Spot (leave empty if not using Spot yet)
    kraken_key: str = os.getenv("KRAKEN_API_KEY", "")
    kraken_secret: str = os.getenv("KRAKEN_API_SECRET", "")

    # Futures (demo or live)
    kraken_futures_key: str = os.getenv("KRAKEN_FUTURES_API_KEY", "")
    kraken_futures_secret: str = os.getenv("KRAKEN_FUTURES_API_SECRET", "")

settings = Settings()