# src/exchange/kraken_ws.py  (public WS subscribe to ticker)
import asyncio, json, websockets
from loguru import logger

WS_URL = "wss://ws.kraken.com"

async def subscribe_ticker(pairs=("XBT/USDT",)):
    # Kraken WS expects pair notation e.g., "XBT/USDT" or "XBT/USD"
    sub = {"event":"subscribe","pair": list(pairs),"subscription":{"name":"ticker"}}
    async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(sub))
        logger.info("Subscribed: {}", sub)
        for _ in range(5):  # read a few messages just to validate plumbing
            msg = await ws.recv()
            logger.info("WS: {}", msg)