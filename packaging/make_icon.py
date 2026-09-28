"""Draw the Lipi icon (लि on a blue tile) as packaging/lipi.ico.

Run on a Mac (uses the Kohinoor Devanagari font). PyMuPDF's HTML layout shapes Devanagari properly,
so the ि sign sits before ल; Pillow alone can't do that. The .ico is committed, so builds don't run this.
"""
import io
from pathlib import Path

import pymupdf
from PIL import Image

FONT = "/System/Library/Fonts/Kohinoor.ttc"
doc = pymupdf.open()
page = doc.new_page(width=256, height=256)
page.draw_rect(pymupdf.Rect(8, 8, 248, 248), color=None, fill=(59 / 255, 91 / 255, 219 / 255), radius=0.22)
css = f"@font-face {{font-family: d; src: url({FONT});}} p {{font-family: d; font-size: 150px; color: white; text-align: center; margin: 0;}}"
page.insert_htmlbox(pymupdf.Rect(0, 44, 256, 256), "<p>लि</p>", css=css)
pix = page.get_pixmap(dpi=72, alpha=True, clip=page.rect)
img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")  # alpha=True: corners stay transparent
out = Path(__file__).parent / "lipi.ico"
img.save(out, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save(Path(__file__).parent / "lipi.png")
print("wrote", out)
