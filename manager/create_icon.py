"""Create the Windows application icon used by PyInstaller and Inno Setup."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    output = Path(__file__).parent / "assets" / "byparr-manager.ico"
    output.parent.mkdir(parents=True, exist_ok=True)
    images = []

    for size in (16, 24, 32, 48, 64, 128, 256):
        image = Image.new("RGBA", (size, size), (16, 20, 28, 255))
        draw = ImageDraw.Draw(image)
        margin = max(1, size // 16)
        draw.rounded_rectangle(
            (margin, margin, size - margin - 1, size - margin - 1),
            radius=max(2, size // 5),
            fill=(35, 53, 83, 255),
            outline=(76, 111, 190, 255),
            width=max(1, size // 32),
        )
        try:
            font = ImageFont.truetype("arialbd.ttf", max(10, int(size * 0.62)))
        except OSError:
            font = ImageFont.load_default()
        text = "B"
        bounds = draw.textbbox((0, 0), text, font=font, stroke_width=0)
        x = (size - (bounds[2] - bounds[0])) / 2 - bounds[0]
        y = (size - (bounds[3] - bounds[1])) / 2 - bounds[1] - size * 0.04
        draw.text((x, y), text, font=font, fill=(235, 242, 255, 255))
        images.append(image)

    images[-1].save(output, format="ICO", sizes=[(im.width, im.height) for im in images])
    print(f"Created {output}")


if __name__ == "__main__":
    main()
