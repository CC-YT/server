from typing import TypedDict, Literal

class InitMsg(TypedDict):
    type: Literal["init"]
    width: int
    height: int
    fps: int

class GetFramesMsg(TypedDict):
    type: Literal["get_frames"]

class GetAudioMsg(TypedDict):
    type: Literal["get_audio"]

class GetMediaMsg(TypedDict):
    type: Literal["get_media"]
    url: str

class StopMsg(TypedDict):
    type: Literal["stop"]

Message = InitMsg | GetFramesMsg | GetAudioMsg | GetMediaMsg | StopMsg