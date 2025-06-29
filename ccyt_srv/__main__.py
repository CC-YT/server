import asyncio, logging, yaml, argparse, sys
from functools import partial
from pathlib import Path
from websockets.asyncio.server import serve

from ccyt_srv.handlers.connection import handle_connection

def parse_args():
    """
    Parse optional commandline arguments
    """
    parser = argparse.ArgumentParser(description="CC:Tweaked Video Player Server")
    parser.add_argument(
        "--host",
        type=str,
        help="Host address to bind the server to (overrides config file)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port number to bind the server to (overrides config file)"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parents[1] / "config.yaml",
        help="Path to the configuration YAML file"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    return parser.parse_args()

def setup_logging(level: str):
    LOG_FILE = Path(__file__).parent / "server.log"
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_FILE, mode='a'),
            logging.StreamHandler()
        ]
    )

def load_config(path: Path) -> dict:
    """
    Find and load a config.yaml
    """
    if not path.exists():
        logging.warning(f"Config file {path} is not found, using default settings")
        return { }
    with open(path, 'r') as f:
        return yaml.safe_load(f) or { }

def merge_settings(config: dict, args: argparse.Namespace) -> dict:
    """
    Merge settings from config.yaml (if it exists), and commandline args

    If neither are present, safe defaults are selected
    """
    server_cfg = config.get("server", {})
    video_cfg = config.get("video", {})
    return {
        "host": args.host or server_cfg.get("host", "0.0.0.0"),
        "port": args.port or server_cfg.get("port", "5000"),
        "compression": "deflate" if server_cfg.get("compression") else None,
        "max_queue": server_cfg.get("max_queue", 3),

        "frame_chunk_size": video_cfg.get("frame_chunk_size", 5),
        "audio_chunk_size": video_cfg.get("audio_chunk_size", 1024),
    }

async def main():
    args = parse_args()
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    config = load_config(args.config)
    settings = merge_settings(config, args)

    logger.info(f"Starting server with settings: {settings}")

    server = await serve(
        partial(handle_connection, settings = settings),
        settings["host"],
        settings["port"],
        compression=settings["compression"]
    )
    logger.info(f"Server listening on {settings['host']}:{settings['port']}")
    
    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        logger.info("Server task cancelled.")
    finally:
        server.close()
        await server.wait_closed()
        logger.info("Server closed.")

def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown requested by user, exiting cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    run()