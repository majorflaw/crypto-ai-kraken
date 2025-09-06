import asyncio, tomllib
from loguru import logger
from src.execution.paper_engine import PaperEngine, EngineConfig
from src.strategies.ema_atr import EMAATRParams

def load_cfg(path="configs/config.toml") -> EngineConfig:
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    run = cfg["run"]
    products = cfg["symbols"]["products"]
    strat = cfg["strategy"]
    risk = cfg["risk"]
    params = EMAATRParams(
        fast=int(strat["fast"]),
        slow=int(strat["slow"]),
        atr_period=int(strat["atr_period"]),
        atr_mult=float(strat["atr_mult"]),
        fee_bps=float(strat["fee_bps"]),
    )
    return EngineConfig(
        products=products,
        base_tf=run["base_tf"],
        target_tf=run["target_tf"],
        log_dir=run["log_dir"],
        trades_csv=run["trades_csv"],
        params=params,
        daily_loss_limit_pct=float(risk["daily_loss_limit_pct"]),
    )

async def main():
    cfg = load_cfg()
    logger.info(f"Starting Paper Engine | products={cfg.products} target_tf={cfg.target_tf}")
    engine = PaperEngine(cfg)
    await engine.run()

if __name__ == "__main__":
    asyncio.run(main())