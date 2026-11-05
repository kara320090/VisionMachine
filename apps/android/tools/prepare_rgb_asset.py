"""Stage the reviewed private ONNX model; never download or commit weights."""
from pathlib import Path
import argparse,hashlib,json,shutil

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    args=parser.parse_args()
    assets=Path(__file__).resolve().parents[1]/'app/src/main/assets'
    card=json.loads((assets/'vision_rgb_model.json').read_text(encoding='utf-8'))
    source=args.model.resolve(strict=True)
    actual=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
    if actual!=card['model_sha256']:raise SystemExit('Model SHA-256 differs from the reviewed model card; asset not staged.')
    target=assets/'vision_rgb_cseed42.onnx'
    if source!=target.resolve():shutil.copyfile(source,target)
    print('Verified private model staged. Do not commit the .onnx file.')

if __name__=='__main__':main()
