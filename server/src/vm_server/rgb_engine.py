"""The Android C_seed42 RGB adapter. No guessed layouts or fallback models."""
import hashlib
import io
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CARD_PATH = ROOT / "apps/android/app/src/main/assets/vision_rgb_model.json"


def crop_rgb(image):
    from PIL import Image, ImageOps
    image = ImageOps.exif_transpose(image).convert("RGB")
    w, h = image.size
    rw, rh = (256, 256 * h // w) if w <= h else (256 * w // h, 256)
    image = image.resize((rw, rh), Image.Resampling.BICUBIC)
    left, top = round((rw - 224) / 2), round((rh - 224) / 2)
    return image.crop((left, top, left + 224, top + 224))


def preprocess(image):
    import numpy as np
    image = crop_rgb(image)
    x = np.asarray(image, dtype=np.float32) / np.float32(255)
    x = (x - np.array([.485, .456, .406], dtype=np.float32)) / np.array([.229, .224, .225], dtype=np.float32)
    return np.ascontiguousarray(x.transpose(2, 0, 1)[None])


class RgbEngine:
    def __init__(self):
        import onnxruntime as ort
        self.card = json.loads(CARD_PATH.read_text())
        self.path = Path(os.environ.get("VM_RGB_MODEL_PATH", str(CARD_PATH.with_name("vision_rgb_cseed42.onnx"))))
        if not self.path.is_file():
            raise RuntimeError(f"MODEL_MISSING: {self.path}")
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != self.card["model_sha256"]:
            raise RuntimeError("MODEL_HASH_MISMATCH")
        ort.preload_dlls(directory="")
        if "CUDAExecutionProvider" not in ort.get_available_providers():
            raise RuntimeError("CUDA_PROVIDER_UNAVAILABLE")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.enable_profiling = os.environ.get("VM_RGB_PROFILE") == "1"
        if options.enable_profiling:
            options.profile_file_prefix = os.environ.get("VM_RGB_PROFILE_PREFIX", "storage/rgb-profile")
        self.session = ort.InferenceSession(str(self.path), sess_options=options,
            providers=[("CUDAExecutionProvider", {"gpu_mem_limit": 2 * 1024**3, "use_tf32": "0",
                        "cudnn_conv_algo_search": "HEURISTIC", "cudnn_conv_use_max_workspace": "0"}),
                       "CPUExecutionProvider"])
        self.session.disable_fallback()
        self.providers = self.session.get_providers()
        if "CUDAExecutionProvider" not in self.providers:
            raise RuntimeError("CUDA_SESSION_UNAVAILABLE")
        inputs, outputs = self.session.get_inputs(), self.session.get_outputs()
        if len(inputs) != 1 or inputs[0].name != "image" or inputs[0].shape != [1, 3, 224, 224] or inputs[0].type != "tensor(float)":
            raise RuntimeError("MODEL_INPUT_CONTRACT_MISMATCH")
        if len(outputs) != 1 or outputs[0].shape != [1, 2] or outputs[0].type != "tensor(float)":
            raise RuntimeError("MODEL_OUTPUT_CONTRACT_MISMATCH")
        self.output_name = outputs[0].name

    def infer(self, raw):
        import numpy as np
        from PIL import Image
        started = time.monotonic()
        with Image.open(io.BytesIO(raw)) as image:
            x = preprocess(image)
        p = np.asarray(self.session.run([self.output_name], {"image": x})[0])
        if p.shape != (1, 2) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any() or abs(float(p.sum()) - 1) > 1e-4:
            raise RuntimeError("INVALID_MODEL_OUTPUT")
        return {"normal": float(p[0, 0]), "abnormal": float(p[0, 1]),
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "model_version": self.card["model_version"], "model_sha256": self.card["model_sha256"]}
