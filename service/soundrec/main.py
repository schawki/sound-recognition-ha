"""Entry point: python -m soundrec --config /config/config.yaml"""
import argparse
import asyncio
import logging
import os
import signal

from aiohttp import web

from .api import make_app
from .engine import Engine


async def run(args):
    eng = Engine(args.config, args.model, args.catalog)
    await eng.start()
    runner = web.AppRunner(make_app(eng))
    await runner.setup()
    api = eng.cfg["api"]
    await web.TCPSite(runner, api["host"], api["port"]).start()
    logging.getLogger("soundrec").info("listening on %s:%s, %d source(s)", api["host"], api["port"], len(eng.pipes))
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, stop.set)
    await stop.wait()
    await eng.stop()
    await runner.cleanup()


def main():
    ap = argparse.ArgumentParser(prog="soundrec")
    ap.add_argument("--config", default=os.environ.get("SOUNDREC_CONFIG", "/config/config.yaml"))
    ap.add_argument("--model", default=os.environ.get("SOUNDREC_MODEL", "/opt/models/yamnet.tflite"))
    ap.add_argument("--catalog", default=os.environ.get("SOUNDREC_CATALOG"))
    ap.add_argument("--log-level", default=os.environ.get("SOUNDREC_LOG", "INFO"))
    args = ap.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
