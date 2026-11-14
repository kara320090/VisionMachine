"""Restore the exact existing Android ONNX from its registered C_seed42 checkpoint.

Export environment verified with torch 2.14.1+cpu, torchvision 0.29.1+cpu,
onnx 1.23.2. No training, download, model-card change or archive mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

def main():
    root = Path(__file__).resolve().parents[1]
    card = json.loads((root / "apps/android/app/src/main/assets/vision_rgb_model.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=root / "ComputerVision-ai/runs/C_seed42/checkpoints/best.pt")
    parser.add_argument("--output", type=Path, default=root / "apps/android/app/src/main/assets/vision_rgb_cseed42.onnx")
    args = parser.parse_args()
    if hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() != card["checkpoint_sha256"]:
        raise SystemExit("Checkpoint differs from the registered app model")
    import torch
    from torch import nn
    sys.path.insert(0, str(root / "ComputerVision-ai/code"))
    from learning import model
    net = model(False)
    # Only deserialize after the existing checkpoint's full SHA-256 is verified.
    net.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=False)["model"], strict=True)
    class RGB(nn.Module):
        def __init__(self, net):
            super().__init__()
            self.net = net
        def forward(self, image):
            return self.net(image).softmax(dim=1)
    torch.set_num_threads(2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".partial.onnx")
    try:
        with torch.inference_mode():
            torch.onnx.export(RGB(net).eval(), (torch.zeros(1, 3, 224, 224),), str(temporary),
                              input_names=["image"], output_names=["probabilities"],
                              opset_version=17, dynamo=False, do_constant_folding=True, export_params=True)
        actual = hashlib.sha256(temporary.read_bytes()).hexdigest()
        if actual != card["model_sha256"]:
            raise SystemExit("Export bytes differ from the existing app model; model card was not changed")
        temporary.replace(args.output)
        print(json.dumps({"model_sha256": actual, "matches_registered_android_model": True, "new_training": False}))
    finally:
        temporary.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
