"""Local server for the portal kiosk: serves portal/ on localhost and turns a captured empty scene
into generated worlds in the background.

    python -m crossover.portal_server                 # http://localhost:8000
    python -m crossover.portal_server --no-generate   # shader worlds only (no model download)

The page POSTs its captured plate to /api/plate; a worker thread generates one world per style
(Stable Diffusion + ControlNet, crossover/generate.py) and the page picks each up from /api/worlds
as soon as it is written. Everything stays on this machine.
"""
from __future__ import annotations

import argparse
import json
import os
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np

PORTAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "portal")
LABELS = {"vangogh": "Van Gogh", "cyberpunk": "Cyberpunk", "winter": "Winter (generated)",
          "night": "Night (generated)", "1920s": "1920s (generated)", "autumn": "Autumn", "comic": "Comic book"}


class Jobs:
    """One generation job at a time; a new plate cancels the previous job."""

    def __init__(self, runtime_dir: str, styles, generate_fn=None):
        self.runtime_dir, self.styles = runtime_dir, list(styles)
        self.generate_fn = generate_fn            # (plate, styles, out_dir, on_done, should_stop) -> None
        self.lock = threading.Lock()
        self.job, self.worlds, self.progress, self.cancel = None, [], "", None

    def start(self, plate: np.ndarray) -> str:
        job = time.strftime("%Y%m%d-%H%M%S")
        out = os.path.join(self.runtime_dir, job)
        os.makedirs(out, exist_ok=True)
        cv2.imwrite(os.path.join(out, "plate.png"), plate)
        with self.lock:
            if self.cancel is not None:
                self.cancel.set()
            cancel = threading.Event()
            self.job, self.worlds, self.cancel = job, [], cancel
            self.progress = "no generator" if self.generate_fn is None else f"generating 0/{len(self.styles)}"
        if self.generate_fn is not None:
            threading.Thread(target=self._run, args=(job, plate, out, cancel), daemon=True).start()
        return job

    def _run(self, job, plate, out, cancel):
        def on_done(style, path):
            with self.lock:
                if self.job != job:
                    return
                rel = os.path.relpath(path, PORTAL_DIR).replace(os.sep, "/")
                self.worlds.append({"style": style, "label": LABELS.get(style, style), "url": f"./{rel}"})
                n = len(self.worlds)
                self.progress = f"generated {n}/{len(self.styles)}" if n < len(self.styles) else ""
        try:
            self.generate_fn(plate, self.styles, out, on_done, cancel.is_set)
        except Exception as e:                              # keep the kiosk running
            with self.lock:
                if self.job == job:
                    self.progress = f"generation failed: {e}"

    def status(self, job: str | None = None) -> dict:
        with self.lock:
            if job and job != self.job:
                return {"job": self.job, "worlds": [], "progress": ""}
            return {"job": self.job, "worlds": list(self.worlds), "progress": self.progress}


def default_generator(device: str, max_width: int):
    """The real generator, loading the pipeline once and reusing it across jobs."""
    from .generate import load_pipeline, pick_device, restyle_plate
    state, lock = {}, threading.Lock()

    def run(plate, styles, out_dir, on_done, should_stop):
        with lock:                    # a cancelled job finishes its current world before the next starts
            if should_stop():
                return
            if "pipe" not in state:
                state["pipe"] = load_pipeline(device=pick_device(device))
            restyle_plate(plate, styles, out_dir, pipe=state["pipe"], max_width=max_width, on_done=on_done,
                          should_stop=should_stop)
    return run


def make_handler(jobs: Jobs, portal_dir: str = PORTAL_DIR):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=portal_dir, **kw)

        def log_message(self, fmt, *args):            # quiet
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def end_headers(self):
            if self.path.startswith("/runtime/"):
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/api/status":
                return self._json({"server": True, "generator": jobs.generate_fn is not None, "styles": jobs.styles})
            if u.path == "/api/worlds":
                return self._json(jobs.status(parse_qs(u.query).get("job", [None])[0]))
            return super().do_GET()

        def do_POST(self):
            if urlparse(self.path).path != "/api/plate":
                return self._json({"error": "not found"}, 404)
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0 or n > 50_000_000:
                return self._json({"error": "bad size"}, 400)
            plate = cv2.imdecode(np.frombuffer(self.rfile.read(n), np.uint8), cv2.IMREAD_COLOR)
            if plate is None:
                return self._json({"error": "not an image"}, 400)
            return self._json({"job": jobs.start(plate)})

    return Handler


def serve(port: int, jobs: Jobs, host: str = "127.0.0.1", portal_dir: str = PORTAL_DIR) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(jobs, portal_dir))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Serve the portal kiosk and generate worlds from its captured scene.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--styles", default="vangogh,cyberpunk,winter,night,1920s")
    ap.add_argument("--device", default="auto", help="auto, cuda, mps or cpu")
    ap.add_argument("--max-width", type=int, default=768, help="generation width (results are resized back)")
    ap.add_argument("--no-generate", action="store_true", help="serve only; the page uses its shader worlds")
    a = ap.parse_args(argv)
    runtime = os.path.join(PORTAL_DIR, "runtime")
    gen = None if a.no_generate else default_generator(a.device, a.max_width)
    jobs = Jobs(runtime, a.styles.split(","), gen)
    httpd = serve(a.port, jobs)
    print(f"Portal: http://localhost:{a.port}/   (Ctrl+C to stop)")
    if gen is not None:
        print(f"Worlds will be generated for each captured scene: {a.styles}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
