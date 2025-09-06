# src/app_futures_demo.py
import asyncio
from loguru import logger
from src.exchange.kraken_futures_ws import subscribe_ticker_and_book

async def main():
    logger.info("Connecting to Kraken Futures Demo WS…")
    await subscribe_ticker_and_book()

if __name__ == "__main__":
    asyncio.run(main())