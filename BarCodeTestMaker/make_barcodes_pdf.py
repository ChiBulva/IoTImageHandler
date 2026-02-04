#!/usr/bin/env python3
"""
Generate a single PDF containing barcodes from ./test_strings.txt

- Reads one string per line
- Numbers each entry
- Renders barcode with the string underneath
- Outputs: barcodes.pdf

Requires:
  pip install python-barcode pillow reportlab
"""

from pathlib import Path
from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from PIL import Image
import io

INFILE = Path("./test_strings.txt")
OUTPDF = Path("./barcodes.pdf")


def read_strings(path: Path) -> list[str]:
    return [l.strip() for l in path.read_text().splitlines() if l.strip()]


def barcode_image(value: str) -> Image.Image:
    buffer = io.BytesIO()
    code = Code128(value, writer=ImageWriter())
    code.write(
        buffer,
        options={
            "module_width": 0.35,
            "module_height": 2.0,
            "quiet_zone": 4.0,
            "write_text": True,
        },
    )
    buffer.seek(0)
    return Image.open(buffer)


def main():
    values = read_strings(INFILE)
    if not values:
        raise ValueError("test_strings.txt is empty")

    c = canvas.Canvas(str(OUTPDF), pagesize=LETTER)
    page_w, page_h = LETTER

    y = page_h - 72  # top margin

    for i, val in enumerate(values, start=1):
        img = barcode_image(val)
        img_w, img_h = img.size

        scale = 300 / img_w
        draw_w = img_w * scale
        draw_h = img_h * scale

        if y - draw_h < 72:
            c.showPage()
            y = page_h - 72

        c.drawInlineImage(img, 72, y - draw_h, draw_w, draw_h)
        c.drawString(72, y - draw_h - 14, f"{i:02d}. {val}")

        y -= draw_h + 40

    c.save()
    print(f"PDF written to {OUTPDF.resolve()}")


if __name__ == "__main__":
    main()
