import asyncio, json, websockets, random
from loguru import logger

WS_URL = "wss://demo-futures.kraken.com/ws/v1"  # Demo env. Live: futures.kraken.com/ws/v1
PRODUCTS = ["PI_XBTUSD", "PI_ETHUSD"]

PING_SECONDS = 55  # per docs: ping at least every 60s to keep alive
CONNECT_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=10)

def _j(obj):  # compact JSON for logs
    return json.dumps(obj, separators=(",", ":"))

async def _send_ping(ws):
    while True:
        try:
            await ws.send(_j({"event": "ping"}))  # app-level ping
            logger.debug("WS -> ping")
        except Exception as e:
            logger.warning(f"Ping failed, stopping pinger: {e}")
            return
        await asyncio.sleep(PING_SECONDS)

def _subscription_messages(products):
    return [
        {"event": "subscribe", "feed": "ticker", "product_ids": products},
        {"event": "subscribe", "feed": "book",   "product_ids": products},
    ]

async def _read_forever(ws):
    """Read and handle messages indefinitely."""
    while True:
        raw = await ws.recv()
        try:
            msg = json.loads(raw)
        except Exception:
            logger.warning(f"WS: non-JSON message: {raw}")
            continue

        # Message routing (all observed in your logs)
        if isinstance(msg, dict) and "event" in msg:
            ev = msg["event"]
            if ev in ("info", "subscribed", "unsubscribed"):
                logger.info(f"WS: {msg}")
            elif ev == "alert":
                # Server thought some prior frame was malformed; just log and continue.
                logger.warning(f"WS ALERT: {msg}")
            elif ev == "pong":
                logger.debug("WS <- pong")
            else:
                logger.debug(f"WS event: {msg}")
            continue

        # Non-event data frames (ticker/book/book_snapshot)
        if isinstance(msg, dict):
            feed = msg.get("feed")
            if feed == "ticker":
                # Minimal example: log best bid/ask and mark price
                logger.info(f"TICK {msg.get('product_id')}: bid {msg.get('bid')} ask {msg.get('ask')} mark {msg.get('markPrice')}")
            elif feed in ("book_snapshot", "book"):
                # Just prove we can parse; full orderbook maint. comes later
                logger.info(f"BOOK {msg.get('product_id')} seq={msg.get('seq')} feed={feed}")
            else:
                logger.debug(f"WS data: {msg}")
        else:
            logger.debug(f"WS frame: {msg}")

async def subscribe_ticker_and_book(products=PRODUCTS):
    """Connect, subscribe, keep alive, and auto-reconnect with jittered backoff."""
    backoff = 1
    while True:
        try:
            logger.info(f"Connecting to {WS_URL} …")
            async with websockets.connect(WS_URL, **CONNECT_KW) as ws:
                # Start keepalive pings
                pinger = asyncio.create_task(_send_ping(ws))
                # Send subscriptions
                for sub in _subscription_messages(products):
                    await ws.send(_j(sub))
                    logger.info(f"Subscribed: {sub}")

                # Reset backoff after successful connect
                backoff = 1
                await _read_forever(ws)
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as e:
            logger.warning(f"WS closed: {e}")
        except Exception as e:
            logger.exception(f"WS error: {e}")

        # Reconnect with capped exponential backoff + jitter
        sleep_s = min(30, backoff) + random.random()
        logger.info(f"Reconnecting in {sleep_s:.1f}s …")
        await asyncio.sleep(sleep_s)
        backoff = min(30, backoff * 2)