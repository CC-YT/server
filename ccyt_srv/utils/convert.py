import numpy as np
from PIL import Image
import subprocess
import os
from itertools import chain
import dfpwm as df
import soundfile as sf

# The 16 colors supported by cc monitors.
#   These can be modified if the client changes the color with setPaletteColour (https://tweaked.cc/module/term.html#v:setPaletteColour)
#   The defaults are going to be used for now
colors = [
    (240,240,240), #white
    (242,178,51), #orange
    (229,127,216), #magenta
    (153,178,242), #lightBlue
    (222,222,108), #yellow
    (127, 204, 25), #lime
    (242, 178, 204), #pink
    (76, 76, 76), #gray
    (153, 153, 153), #lightGray
    (76, 153, 178), #cyan
    (178, 102, 229), #purple
    (51, 102, 204), #blue
    (127, 102, 76), #brown
    (87, 166, 78), #green
    (204, 76, 76), #red
    (17, 17, 17), #black
]

palette_bytes = list(chain.from_iterable(colors))
pal_img = Image.new("P", (16,1))
pal_img.putpalette(palette_bytes)

def parse_video(path, width: int, height: int, fps: int, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    subprocess.run([
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", path,
        "-vf", f"scale={width}:{height}:flags=lanczos,fps={fps}",
        os.path.join(output_dir,"out_%05d.png")
    ])

    au_path = os.path.join(output_dir,"audio.wav")
    subprocess.run([
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", path,
        "-ac", "1", #dfpwm only supports 1 audio channel
        "-ar", "48000", #dfpwm also likes a 48kHz sample rate
        au_path
    ])
    data, sample_rate = sf.read(au_path)
    dfpwm_bytes = df.compressor(data)

    with open(os.path.join(output_dir,"audio.dfpwm"), "wb") as out:
        out.write(dfpwm_bytes)

def convert_img(path):
    img = Image.open(path).convert("RGB")

    iq = img.quantize(palette=pal_img, dither=Image.NONE)
    data = iq.load()

    width, height = iq.size

    lines = []
    for y in range(height):
        bg_line = "".join(f"{data[x,y]:x}" for x in range(width))
        lines.append(f"{bg_line}")
    
    return "\n".join(lines)