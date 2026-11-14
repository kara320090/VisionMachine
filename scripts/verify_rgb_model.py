"""Verify the real, hash-pinned model and CUDA node execution; never create a model."""
import argparse
import io
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
source = parser.add_mutually_exclusive_group(required=True)
source.add_argument("--photo", type=Path)
source.add_argument("--synthetic-probe", action="store_true", help="Synthetic image tests execution, not accuracy")
parser.add_argument("--report", type=Path, required=True)
args = parser.parse_args()
profile_dir = Path("storage/model-verification").resolve()
profile_dir.mkdir(parents=True, exist_ok=True)
os.environ["VM_RGB_PROFILE"] = "1"
os.environ["VM_RGB_PROFILE_PREFIX"] = str(profile_dir / "profile")
from vm_server.rgb_engine import RgbEngine

try:
    engine = RgbEngine()  # Missing/hash-mismatched ONNX fails before any probe is generated.
except Exception as error:
    args.report.write_text(json.dumps({"app_model_inference_verified": False, "reason": str(error)}, indent=2) + "\n")
    raise SystemExit(str(error)) from None
if args.photo:
    raw = args.photo.read_bytes()
else:
    from PIL import Image
    output = io.BytesIO()
    Image.new("RGB", (71, 53), (34, 119, 68)).save(output, "PNG")
    raw = output.getvalue()
result = engine.infer(raw)
profile_path = engine.session.end_profiling()
events = json.loads(Path(profile_path).read_text())
cuda_nodes = [e for e in events if e.get("cat") == "Node" and e.get("args", {}).get("provider") == "CUDAExecutionProvider"]
if not cuda_nodes:
    raise SystemExit("No CUDA node execution was recorded")
report = {"app_model_inference_verified": True, "model_sha256": engine.card["model_sha256"], "providers": engine.providers,
          "inputs": [{"name": i.name, "shape": i.shape, "type": i.type} for i in engine.session.get_inputs()],
          "outputs": [{"name": i.name, "shape": i.shape, "type": i.type} for i in engine.session.get_outputs()],
          "cuda_profile_node_events": len(cuda_nodes), "result": result,
          "input_kind": "synthetic_execution_probe" if args.synthetic_probe else "supplied_photo",
          "field_accuracy_verified": False}
args.report.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
