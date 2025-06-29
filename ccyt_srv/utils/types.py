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

Message = InitMsg | GetFramesMsg | GetAudioMsg