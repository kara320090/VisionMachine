"""Compile and run the real bounded request decoder on the host; no board upload."""
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    compiler = next((path for name in ("c++", "g++", "clang++", "cl")
                     if (path := shutil.which(name))), None)
    if compiler is None:
        raise SystemExit("Install a C++ compiler or use an MSVC Developer Command Prompt.")
    sources = [ROOT / "firmware/MeasureRequest.cpp", ROOT / "tests/firmware/measure_request_test.cpp"]
    with tempfile.TemporaryDirectory(prefix="vm-firmware-test-") as folder:
        directory = Path(folder)
        binary = directory / "measure_request_test.exe"
        if Path(compiler).stem.lower() == "cl":
            flags = ["/nologo", "/EHsc", "/std:c++14", "/W4", "/WX", "/utf-8",
                     "/I" + str(ROOT / "firmware"), "/Fe:" + str(binary)]
        else:
            flags = ["-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                     "-I", str(ROOT / "firmware"), "-o", str(binary)]
        subprocess.run([compiler, *flags, *map(str, sources)], cwd=directory, check=True)
        subprocess.run([str(binary)], cwd=directory, check=True)


if __name__ == "__main__":
    main()
