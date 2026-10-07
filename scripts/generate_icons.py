"""Generate tray, bundle, and installer icons (Hybrid 4 mark A — ink tile + lime arrow)."""
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SOURCE_NAME = "icon-source.png"
BUNDLE_SIZE = 1024
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# Soft Sage canvas — matches Trade Desky marketing / NT receiver installer.
SAGE = (242, 244, 241)
INK = (17, 17, 17, 255)
LIME = (34, 197, 94, 255)

WELCOME_SIZE = (164, 314)
HEADER_SIZE = (150, 57)


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


def _paste_centered(canvas: Image.Image, mark: Image.Image, *, max_side: int, y: int | None = None) -> None:
    side = min(max_side, canvas.size[0] - 16, canvas.size[1] - 16)
    logo = mark.resize((side, side), Image.Resampling.LANCZOS)
    x = (canvas.size[0] - side) // 2
    top = y if y is not None else (canvas.size[1] - side) // 2
    canvas.paste(logo, (x, top), logo)


def write_welcome_bitmap(assets: Path, mark: Image.Image) -> Path:
    canvas = Image.new("RGB", WELCOME_SIZE, SAGE)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, WELCOME_SIZE[0], 8), fill=INK)
    _paste_centered(canvas, mark, max_side=112, y=56)
    path = assets / "installer-welcome.bmp"
    canvas.save(path, format="BMP")
    return path


def write_header_bitmap(assets: Path, mark: Image.Image) -> Path:
    canvas = Image.new("RGB", HEADER_SIZE, SAGE)
    side = 44
    logo = mark.resize((side, side), Image.Resampling.LANCZOS)
    x = HEADER_SIZE[0] - side - 6
    y = (HEADER_SIZE[1] - side) // 2
    canvas.paste(logo, (x, y), logo)
    path = assets / "installer-header.bmp"
    canvas.save(path, format="BMP")
    return path


def write_icons(assets: Path) -> tuple[Path, ...]:
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
    welcome = write_welcome_bitmap(assets, base)
    header = write_header_bitmap(assets, base)
    return png_path, ico_path, welcome, header


def main() -> None:
    paths = write_icons(ASSETS)
    print("Wrote", ", ".join(str(p) for p in paths))


if __name__ == "__main__":
    main()
