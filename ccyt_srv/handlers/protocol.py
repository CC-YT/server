import asyncio
import json
import tempfile
import os
import base64
import logging
from pathlib import Path
from yt_dlp import YoutubeDL
from websockets.asyncio.server import ServerConnection
from ccyt_srv.handlers.connection import ConnectionState
from ccyt_srv.utils.convert import convert_img, parse_video
from ccyt_srv.utils.types import InitMsg, GetMediaMsg

logger = logging.getLogger(__name__)

# Async task to fill up the queue with frames up to maxsize
async def process_frames(state: ConnectionState):
    for fn in state.frame_files:
        framedata = convert_img(state.tmpdir / fn)
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

    Basically just creates the connection state
    """
    fps = int(data.get("fps"))
    width = int(data.get("width"))
    height = int(data.get("height"))

    tmpdir = Path(tempfile.mkdtemp(prefix="ccyt."))
    logger.info(f"Created temp directory for connection: {tmpdir}")

    state = ConnectionState(tmpdir,width,height,fps,settings)
    logger.info(f"Created connection state")
    #logger.info(f"Telling client that the server is initialized")
    #await ws.send(json.dumps({
    #    "type": "init_done"
    #}))
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

async def handle_get_media(
    ws: ServerConnection,
    data: GetMediaMsg,
    state: ConnectionState,
    settings: dict
) -> None:
    """
    Handles "get_media" message from the client

    Uses yt-dlp to download the video url from youtube
    """
    if not (url := data.get("url")):
        logger.warning("Get_Media request had no url")
        await ws.send(json.dumps({
            "type": "error",
            "message": "Missing url in get_media request"
        }))
        return
    
    logger.info(f"Received get_media request for URL: {url}")
    
    # Make the output directory if it doesn't yet exist
    output_dir = state.tmpdir / "media"
    output_dir.mkdir(parents=True,exist_ok=True)
    
    video_path = output_dir / "video.mp4"

    ydl_opts = {
        "format": "worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst",
        "outtmpl": str(video_path),
        "quiet": True,
        "no_warnings": False,
        "merge_output_format": "mp4"
    }

    def download():
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    
    try:
        # Offload blocking function, download, to a background thread
        # so it doesn't block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None,download)
    except Exception as e:
        logger.exception("Error downloading media")
        await ws.send(json.dumps({
            "type": "error",
            "message": f"Download failed: {str(e)}"
        }))
        return
    logger.info(f"Download complete, notifying client")

    # Update the connection state
    state.video_file = video_path

    state.frame_files = parse_video(state.video_file, state.width, state.height, state.fps, state.tmpdir)

    logger.info(f"Beginning process frames task for {ws.remote_address[0]}")
    asyncio.create_task(process_frames(state)) # Begin the process_frames task

    # Tell the client that the server is ready for streaming
    await ws.send(json.dumps({
        "type": "ready"
    }))