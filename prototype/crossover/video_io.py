"""Video reading/writing helpers.

Frames are BGR uint8 numpy arrays (OpenCV convention). Writing goes through an ffmpeg pipe so the
output is a widely playable H.264 mp4 (yuv420p), which cv2.VideoWriter does not reliably produce.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterator

import cv2
import numpy as np


@dataclass
class VideoInfo:
    path: str
    fps: float
    n_frames: int
    width: int   # after scaling
    height: int  # after scaling
    src_width: int
    src_height: int


def _even(x: float) -> int:
    v = int(round(x))
    return v - (v % 2)


def probe(path: str, scale: float = 1.0) -> VideoInfo:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return VideoInfo(path, float(fps), n, _even(w * scale), _even(h * scale), w, h)


def iter_frames(path: str, scale: float = 1.0, max_frames: int | None = None) -> Iterator[np.ndarray]:
    """Yield frames sequentially (decoding sequentially is more reliable than seeking)."""
    info = probe(path, scale)
    cap = cv2.VideoCapture(path)
    i = 0
    try:
        while True:
            if max_frames is not None and i >= max_frames:
                break
            ok, frame = cap.read()
            if not ok:
                break
            if (frame.shape[1], frame.shape[0]) != (info.width, info.height):
                interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
                frame = cv2.resize(frame, (info.width, info.height), interpolation=interp)
            yield frame
            i += 1
    finally:
        cap.release()


class VideoWriter:
    """Context manager: write BGR uint8 frames to an H.264 mp4 through ffmpeg."""

    def __init__(self, path: str, width: int, height: int, fps: float, crf: int = 18):
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg not found on PATH")
        self.path, self.size = path, (width, height)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", f"{fps}",
            "-i", "-",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", path,
        ]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, frame: np.ndarray) -> None:
        if (frame.shape[1], frame.shape[0]) != self.size:
            raise ValueError(f"frame size {frame.shape[1]}x{frame.shape[0]} != writer size {self.size}")
        self.proc.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())

    def close(self) -> None:
        if self.proc.stdin and not self.proc.stdin.closed:
            self.proc.stdin.close()
        if self.proc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed writing {self.path}")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def to_float(img: np.ndarray) -> np.ndarray:
    return img.astype(np.float32) / 255.0


def to_uint8(img: np.ndarray) -> np.ndarray:
    return np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)
