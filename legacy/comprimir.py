from pathlib import Path
from PIL import Image

MAX_DIMENSION = 1920
QUALITY = 80
OUTPUT_DIR = Path("./otimizadas")
OUTPUT_DIR.mkdir(exist_ok=True)

for file in Path(".").glob("*.jpg"):
    if file.is_file():
        with Image.open(file) as img:
            img = img.convert("RGB")
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            dest = OUTPUT_DIR / file.name
            img.save(dest, "JPEG", optimize=True, quality=QUALITY)
            kb = dest.stat().st_size / 1024
            print(f"{file.name} -> {kb:.1f} KB")