import asyncio
import json
import tempfile
import os
import base64
import logging
from websockets.asyncio.server import ServerConnection
from ccyt_srv.handlers.connection import ConnectionState
from ccyt_srv.utils.convert import convert_img, parse_video
from ccyt_srv.utils.types import InitMsg

logger = logging.getLogger(__name__)

# Async task to fill up the queue with frames up to maxsize
async def process_frames(state: ConnectionState):
    for fn in state.frame_files:
        framedata = convert_img(os.path.join(state.tmpdir, fn))
        await state.frame_queue.put(framedata)
        logger.debug(f"Added processed frame {fn} to frame queue")
    logger.info("Frame processing finished")
    await state.frame_queue.put("Done") # Signifies that the processing is done

async def handle_init(
    ws: ServerConnection,
    data: InitMsg,
    settings: dict
) -> ConnectionState:
    """
    Handles "init" message from a client

    Parse init message, start frame processing,
    and return the connection state
    """
    fps = int(data.get("fps"))
    width = int(data.get("width"))
    height = int(data.get("height"))

    tmpdir = tempfile.mkdtemp(prefix="ccyt.")
    logger.info(f"Created temp directory for connection: {tmpdir}")

    parse_video(settings.get("video_file"), width, height, fps, tmpdir)

    state = ConnectionState(tmpdir,width,height,fps,settings)
    asyncio.create_task(process_frames(state)) # Begin the process_frames task
    
    logger.info(f"Sending ready packet to {ws.remote_address[0]}")
    await ws.send(json.dumps({
        "type": "ready"
    }))
    return state

async def handle_get_frames(
    ws: ServerConnection,
    state: ConnectionState
) -> None:
    """
    Handles "get_frames" message from a client

    Pull up to state.f_chunk frames from the state.frame_queue
    and them send them as a JSON packet.
    """
    if not state:
        logger.warning("Connection hasn't been initalized")
        return
    
    chunk = []
    for _ in range(state.f_chunk):
        frame = await state.frame_queue.get()
        if frame == "Done":
            await ws.send(json.dumps({
                "type": "frames_end",
            }))
            break
        chunk.append(frame)
    
    logger.debug(f"Sending a chunk of {len(chunk)} frames")
    await ws.send(json.dumps({
        "type": "frame",
        "data": chunk
    }))

async def handle_get_audio(
    ws: ServerConnection,
    state: ConnectionState
) -> None:
    """
    Handles "get_audio" message from a client

    Pull up to state.a_chunk bytes from the audio file
    at state.audio_path, adjust the state.audio offset accordingly,
    and them send them as a JSON packet.

    Sends an "audio_end" packet if there is nothing more to be sent
    """
    if not state:
        logger.warning("Connection hasn't been initalized")
        return

    with open(state.audio_path, "rb") as af: #af: audio file
        af.seek(state.audio_offset)
        data = af.read(state.a_chunk)
    
    if data:
        state.audio_offset += len(data)
        b64 = base64.b64encode(data).decode()
        logger.debug(f"Sending a {state.a_chunk} byte chunk of audio")
        await ws.send(json.dumps({
            "type": "audio",
            "data": b64
        }))
    else:
        logger.debug("All audio sent, sending audio_end")
        await ws.send(json.dumps({
            "type": "audio_end",
        }))