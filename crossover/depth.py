"""Depth of the empty scene: Depth Anything V2 Small (ONNX, CPU), run once per scene.

It conditions Stable Diffusion (the depth ControlNet in generate.py) and drives the interface's Depth
rule. Depth Anything gives relative disparity (higher = nearer, unknown scale), so it is only used
through quantiles: farness in [0, 1] after percentile normalisation.
"""
from __future__ import annotations

import os

import cv2
import numpy as np

DEFAULT_MODEL = os.path.join(os.path.dirname(__file__), "..", "models", "depth_anything_v2_vits.onnx")
_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_STD = np.array([0.229, 0.224, 0.225], np.float32)


# ------------------------------------------------------------------------------- estimation
def estimate_disparity(img: np.ndarray, model_path: str = DEFAULT_MODEL) -> np.ndarray:
    """Relative disparity (higher = nearer), HxW float32, same size as img (BGR uint8)."""
    import onnxruntime as ort  # optional dependency, only needed for depth mode

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"{model_path} - run scripts/fetch_depth_model.sh")
    h, w = img.shape[:2]
    x = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = cv2.resize(x, (518, 518), interpolation=cv2.INTER_CUBIC)       # as the reference does
    x = ((x - _MEAN) / _STD).transpose(2, 0, 1)[None].astype(np.float32)
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0]
    disp = np.squeeze(out).astype(np.float32)
    return cv2.resize(disp, (w, h), interpolation=cv2.INTER_CUBIC)




def farness(disp: np.ndarray) -> np.ndarray:
    """Percentile-normalised far-ness in [0,1]: 0 = nearest (p98 disparity), 1 = farthest (p2)."""
    lo, hi = np.percentile(disp, [2, 98])
    return np.clip((hi - disp) / (hi - lo + 1e-6), 0, 1).astype(np.float32)




def depth_vis(f: np.ndarray, contour_level: float | None = None) -> np.ndarray:
    """Colour-mapped farness (bright = near), optional white contour at the split level."""
    vis = cv2.applyColorMap(((1 - f) * 255).astype(np.uint8), cv2.COLORMAP_MAGMA)
    if contour_level is not None:
        m = (f >= contour_level).astype(np.uint8)
        cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(vis, cs, -1, (255, 255, 255), max(1, f.shape[1] // 400), cv2.LINE_AA)
    return vis
