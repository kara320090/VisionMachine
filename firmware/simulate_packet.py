"""Print one explicitly mock packet. Does not connect to USB hardware."""
from pathlib import Path
import argparse, json
from uuid import UUID
from vm_contracts.models import SensorPacket

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--request-id",type=UUID,default=UUID("11111111-1111-4111-8111-111111111111"))
args=parser.parse_args()
path=Path(__file__).resolve().parents[1]/"contracts/examples/sensor.mock.json"
data=json.loads(path.read_text(encoding="utf-8"))
data["request_id"]=str(args.request_id)
print(SensorPacket.model_validate(data).model_dump_json())
