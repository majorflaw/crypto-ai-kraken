import asyncio
from loguru import logger
from src.exchange.kraken_futures_rest import fetch_instruments, filter_tradeable_perpetuals

async def main():
    raw = await fetch_instruments()
    perps = filter_tradeable_perpetuals(raw)
    # Show a compact preview
    logger.info(f"Total instruments: {len(raw.get('instruments', []))}")
    logger.info(f"Perpetuals found: {len(perps)}")
    for inst in perps[:10]:
        symbol = inst.get('symbol') or inst.get('product_id')
        tick = inst.get('tickSize') or inst.get('tick_size')
        lot  = inst.get('contractSize') or inst.get('contract_size') or inst.get('quantityIncrement')
        logger.info(f"{symbol} | tick={tick} | lot={lot}")

if __name__ == "__main__":
    asyncio.run(main())