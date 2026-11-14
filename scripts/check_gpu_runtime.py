"""Inspect real GPU libraries without creating or substituting any model."""
import ctypes
import importlib.metadata
import json
from pathlib import Path

import onnxruntime as ort

ort.preload_dlls(directory="")
cuda = ctypes.CDLL("libcuda.so.1")
cuda.cuInit.argtypes = [ctypes.c_uint]
cuda.cuInit.restype = ctypes.c_int
status = cuda.cuInit(0)
if status:
    raise SystemExit(f"cuInit failed: {status}")
count = ctypes.c_int()
status = cuda.cuDeviceGetCount(ctypes.byref(count))
if status or count.value < 1:
    raise SystemExit(f"cuDeviceGetCount: status={status}, count={count.value}")

name = ctypes.create_string_buffer(256)
if cuda.cuDeviceGetName(name, len(name), 0):
    raise SystemExit("cuDeviceGetName failed")
cudnn = ctypes.CDLL("libcudnn.so.9")
cudnn.cudnnGetVersion.restype = ctypes.c_size_t
# Loading the actual provider shared object checks its runtime dependencies.
provider = ctypes.CDLL(str(Path(ort.__file__).parent / "capi/libonnxruntime_providers_cuda.so"))
distributions = ["onnxruntime-gpu", "nvidia-cuda-runtime-cu12", "nvidia-cudnn-cu12",
                 "nvidia-cublas-cu12", "nvidia-cuda-nvrtc-cu12", "nvidia-cufft-cu12",
                 "nvidia-curand-cu12", "nvidia-nvjitlink-cu12"]
report = {
    "packages": {name: importlib.metadata.version(name) for name in distributions},
    "registered_providers": ort.get_available_providers(),
    "cuda_provider_library_loaded": True,
    "cuda_device_count": count.value,
    "cuda_device_0": name.value.decode(),
    "cudnn_version_integer": cudnn.cudnnGetVersion(),
    "app_model_inference_checked_by_this_probe": False,
    "note": "모델을 사용하지 않은 환경 검사입니다. 앱 모델의 세션/입출력/추론 검증은 별도입니다.",
}
print(json.dumps(report, ensure_ascii=False, indent=2))
