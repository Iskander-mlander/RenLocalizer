"""Patch aiohttp __init__.py for Python 3.14 circular import workaround.
Finds aiohttp via pip show without importing it."""

import subprocess, os, sys

result = subprocess.run(
    [sys.executable, "-m", "pip", "show", "aiohttp"], capture_output=True, text=True
)
for line in result.stdout.splitlines():
    if line.lower().startswith("location:"):
        loc = line.split(":", 1)[1].strip()
        p = os.path.join(loc, "aiohttp", "__init__.py")
        with open(p) as f:
            c = f.read()
        c = c.replace("from . import hdrs as hdrs\n", "", 1)
        old = """def __getattr__(name: str) -> object:
    global GunicornUVLoopWebWorker, GunicornWebWorker
    if name in ("GunicornUVLoopWebWorker", "GunicornWebWorker"):"""
        new = """def __getattr__(name: str) -> object:
    global hdrs, GunicornUVLoopWebWorker, GunicornWebWorker
    if name == "hdrs":
        import aiohttp.hdrs as hdrs
        return hdrs
    if name in ("GunicornUVLoopWebWorker", "GunicornWebWorker"):"""
        c = c.replace(old, new, 1)
        with open(p, "w") as f:
            f.write(c)
        print(f"aiohttp patched at {p}")
        sys.exit(0)
print("aiohttp not found")
sys.exit(1)
