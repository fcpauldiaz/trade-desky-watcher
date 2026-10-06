"""Generate tray, bundle, and installer icons (Hybrid 4 mark A — ink tile + lime arrow)."""
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SOURCE_NAME = "icon-source.png"
BUNDLE_SIZE = 1024
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

INK = (17, 17, 17, 255)
LIME = (34, 197, 94, 255)


def draw_mark_a(size: int) -> Image.Image:
    """Match tradedesky public/brand/mark-a.svg (app icon)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 96
    radius = 22 * s
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=INK)

    stroke = max(2, round(8 * s))
    points = [
        (28 * s, 58 * s),
        (48 * s, 32 * s),
        (68 * s, 58 * s),
    ]
    draw.line(points, fill=LIME, width=stroke, joint="curve")
    draw.line([(48 * s, 38 * s), (48 * s, 68 * s)], fill=LIME, width=stroke)
    cap_r = stroke / 2
    for x, y in [
        (28 * s, 58 * s),
        (48 * s, 32 * s),
        (68 * s, 58 * s),
        (48 * s, 38 * s),
        (48 * s, 68 * s),
    ]:
        draw.ellipse((x - cap_r, y - cap_r, x + cap_r, y + cap_r), fill=LIME)
    return img


def load_source(assets: Path) -> Image.Image:
    generated = draw_mark_a(BUNDLE_SIZE)
    source = assets / SOURCE_NAME
    assets.mkdir(parents=True, exist_ok=True)
    generated.save(source)
    return generated


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
