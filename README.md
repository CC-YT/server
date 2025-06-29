# CCYT Server – Video Streaming for CC:Tweaked

This is the Python server component of a **CC:Tweaked video streaming system**, capable of streaming YouTube videos (or any video file) with audio to computers running [CC:Tweaked](https://tweaked.cc/) in Minecraft.

It handles video decoding, conversion, audio compression (DFPWM), and sends frame/audio data to the CC client via WebSockets.

---

## 🚀 Features

- Streams YouTube videos with audio into Minecraft using CC:Tweaked
- Converts video to terminal-optimized colored frames
- DFPWM audio compression for CC speakers
- Works over WebSockets
- Supports frame chunking for performance
- Extensible protocol handler system

---

## 📦 Requirements

### Python version

- **Python 3.11 – 3.13** supported and tested

### Python packages

These are defined in `requirements.txt`, but include:

```text
asyncio==3.4.3
cffi==1.17.1
dfpwm==0.2.0
numpy==2.3.1
pillow==11.2.1
pycparser==2.22
PyYAML==6.0.2
soundfile==0.13.1
websockets==15.0.1
yt-dlp==2025.6.25
````

### System dependency

* `ffmpeg` is **required** for video/audio processing.

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/CC-YT/server.git
cd ccyt-server
```

### 2. Install `ffmpeg`

#### Debian/Ubuntu

```bash
sudo apt update
sudo apt install ffmpeg
```

#### Arch Linux

```bash
sudo pacman -S ffmpeg
```

#### macOS (with Homebrew)

```bash
brew install ffmpeg
```

---

### 3. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## 🧪 Usage

```bash
python -m ccyt_srv --video-file ./video.mp4
```

Or use a YouTube link via `yt-dlp` beforehand:

```bash
yt-dlp -o video.mp4 "https://www.youtube.com/watch?v=your_video_id"
python -m ccyt_srv --video-file ./video.mp4
```

### Optional flags

| Flag                 | Description                          |
| -------------------- | ------------------------------------ |
| `--video-file`, `-v` | Path to the video file to stream     |
| `--host`             | Host to bind the WebSocket server to |
| `--port`             | Port number for the WebSocket server |
| `--log-level`        | Logging level (DEBUG, INFO, etc.)    |
| `--config`           | Path to a custom `config.yaml`       |

---

## ⚙️ Configuration

You can override defaults using `config.yaml`:

```yaml
server:
  host: "127.0.0.1"
  port: 5000
  compression: false
  max_queue: 3

video:
  frame_chunk_size: 9    # In frames
  audio_chunk_size: 1024 # In bytes
```

---

## 📋 License

This project is licensed under the [MIT License](LICENSE).


## 🎮 CC\:Tweaked Client

You’ll need to install the CC client code on a computer in Minecraft. Make sure it has:

* A speaker peripheral
* A connected monitor (preferably large)
* HTTP/WebSocket support enabled in the server config
