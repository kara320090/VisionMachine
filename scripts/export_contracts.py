"""Run from repository root. Exit nonzero when committed schemas drift."""
from pathlib import Path
import argparse, json
from vm_contracts.models import SensorPacket, InspectionMetadata, AnalysisResult

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    changed = []
    for name, model in [("sensor-packet", SensorPacket), ("inspection", InspectionMetadata), ("analysis-result", AnalysisResult)]:
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        body = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path = root / "contracts" / "schemas" / (name + ".schema.json")
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != body:
                changed.append(path.name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
    if changed:
        parser.exit(1, "Outdated schemas: " + ", ".join(changed) + "\n")
    print("Contract schemas verified" if args.check else "Contract schemas exported")

if __name__ == "__main__":
    main()
