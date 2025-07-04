import asyncio
import json
import os
import tempfile
import shutil
import logging
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from websockets.asyncio.server import ServerConnection
from ccyt_srv.utils.types import Message

logger = logging.getLogger(__name__)

class ConnectionState:
    def __init__(self, tmpdir, width, height, fps, settings):
        self.tmpdir = tmpdir
        self.width = width
        self.height = height
        self.fps = fps

        self.video_file = None
        self.frame_files = None
        self.f_chunk = settings["frame_chunk_size"]

        self.frame_queue = asyncio.Queue(maxsize=settings["max_queue"]*self.f_chunk)
        self.current_frame = 0
        self.frame_task = None

        self.audio_path = tmpdir / "audio.dfpwm"
        self.a_chunk = settings["audio_chunk_size"]
        self.audio_offset = 0
        self.audio_duration = 0
        self.audio_bytes = 0

from ccyt_srv.handlers.protocol import *

async def handle_connection(
    websocket: ServerConnection,
    settings: dict
) -> None:
    """
    Handle a single WebSocket client.
    """
    addr = websocket.remote_address[0]
    logger.info(f"Connected to: {addr}")
    state = None
    try:
        async for message in websocket:
            logger.debug(f"Msg from {addr}: {message}")
            try:
                data: Message = json.loads(message)
            except json.JSONDecodeError:
                logger.warning("Received invalid JSON or incorrectly formatted packet")
                continue # Stop current iteration and start over

            # Packet handling
            match data.get("type"):
                case "init":
                    logger.info(f"Initalizing connection: {addr}")
                    state = await handle_init(websocket, data, settings)
                case "get_frames":
                    await handle_get_frames(websocket, state)
                case "get_audio":
                    await handle_get_audio(websocket, state)
                case "get_media":
                    await handle_get_media(websocket, data, state, settings)
                case "stop":
                    state = await handle_stop(websocket,state,settings)
                case "seek":
                    await handle_seek(websocket, data, state)
                case _:
                    logger.warning(f"Unknown message type: {data.get('type')}")
    
    # ERROR Dectection for good error logging
    except ConnectionClosedOK:
        logger.info(f"Client {addr} closed the connection.")
    except ConnectionClosedError as e:
        logger.warning(f"Connection closed with error from {addr}: {e}")
    except asyncio.CancelledError:
        logger.info(f"Connection handler for {addr} was cancelled (server shutdown).")
        raise  # re-raise so upstream shutdown logic works
    except Exception as e:
        logger.exception(f"Unexpected error with client {addr}: {e}")
    finally:
        # Clean-up connection
        if state:
            logger.info("Cleaning up, deleting tmpdir")
            shutil.rmtree(state.tmpdir, ignore_errors=True)
        await websocket.wait_closed()
        logger.info(f"Disconnected from: {websocket.remote_address}")