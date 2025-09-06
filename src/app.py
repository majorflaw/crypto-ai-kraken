# src/app.py  (quick connectivity test runner)
import asyncio
from loguru import logger
from src.agent.groq_client import groq_hello
from src.exchange.kraken_ws import subscribe_ticker
from src.data.ohlc_rest import fetch_ohlc

async def main():
    pong = await groq_hello()
    logger.info(f"Groq says: {pong}")
    await subscribe_ticker(("XBT/USDT","ETH/USDT"))
    df = await fetch_ohlc("XBTUSDT","1h")
    logger.info(df.tail(3).to_string())

if __name__ == "__main__":
    asyncio.run(main())