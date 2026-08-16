"""Generate tray and bundle icons from the Trade Desky mark."""
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SOURCE_NAME = "icon-source.png"
BUNDLE_SIZE = 1024
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def load_source(assets: Path) -> Image.Image:
    source = assets / SOURCE_NAME
    if not source.is_file():
        raise FileNotFoundError(f"Missing {source}")
    image = Image.open(source).convert("RGBA")
    return image.resize((BUNDLE_SIZE, BUNDLE_SIZE), Image.Resampling.LANCZOS)


def write_icons(assets: Path) -> tuple[Path, Path]:
    assets.mkdir(parents=True, exist_ok=True)
    base = load_source(assets)
    png_path = assets / "icon.png"
    base.save(png_path)
    ico_path = assets / "icon.ico"
    base.save(ico_path, format="ICO", sizes=ICO_SIZES)
    icns_path = assets / "icon.icns"
    try:
        base.save(icns_path, format="ICNS")
    except (ValueError, OSError, KeyError):
        base.resize((256, 256), Image.Resampling.LANCZOS).save(assets / "icon.icns.png")
    return png_path, ico_path


def main() -> None:
    png_path, ico_path = write_icons(ASSETS)
    print(f"Wrote {png_path}, {ico_path}")


if __name__ == "__main__":
    main()
