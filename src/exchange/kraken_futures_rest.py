import httpx
from typing import List, Dict, Any
from loguru import logger

INSTRUMENTS_URL = "https://futures.kraken.com/derivatives/api/v3/instruments"  #  [oai_citation:6‡Kraken Documentation](https://docs.kraken.com/api/docs/futures-api/trading/get-instruments?utm_source=chatgpt.com)

async def fetch_instruments() -> Dict[str, Any]:
    """
    Returns the raw payload from Kraken Futures instruments endpoint (public).
    Doc: GET /derivatives/api/v3/instruments
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(INSTRUMENTS_URL)
        r.raise_for_status()
        return r.json()

def filter_tradeable_perpetuals(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filters instruments to tradeable perpetual swaps (e.g., PI_XBTUSD).
    The exact fields can evolve; we keep this defensive.
    """
    instruments = payload.get("instruments") or payload.get("result") or []
    out = []
    for inst in instruments:
        # Common fields: symbol or product_id, tradeable, type/tag might mention "perpetual"
        symbol = inst.get("symbol") or inst.get("product_id") or inst.get("name")
        tradeable = inst.get("tradeable", True)  # default to True if absent (public list is usually tradeable)
        tag = (inst.get("type") or inst.get("contract_type") or inst.get("tag") or "").lower()
        if not symbol:
            continue
        if not tradeable:
            continue
        # Consider as perpetual if name or type shows "perpetual" or symbol starts with PI_
        if "perpetual" in tag or str(symbol).startswith("PI_"):
            out.append(inst)
    return out