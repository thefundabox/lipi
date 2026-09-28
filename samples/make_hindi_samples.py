"""Build Hindi and mixed Hindi+English test PDFs (digital, clean scan, poor scan, phone photo)."""
import cv2
import numpy as np
import pymupdf

from make_samples import rotate

HINDI = ("राजस्थान लोक सेवा आयोग राज्य एवं अधीनस्थ सेवा संयुक्त प्रतियोगी परीक्षा का आयोजन करता है। "
         "अभ्यर्थियों को अंतिम तिथि से पहले आवेदन पत्र जमा करना होगा। प्रवेश पत्र परीक्षा से सात दिन "
         "पहले ऑनलाइन जारी किए जाएंगे। पाठ्यक्रम में राजस्थान और भारत का इतिहास, भूगोल, राजनीति, "
         "अर्थव्यवस्था, विज्ञान तथा समसामयिक घटनाएं शामिल हैं।")
MIXED = ("RAS Prelims 2026: राजस्थान लोक सेवा आयोग (RPSC) ने अधिसूचना जारी की है। "
         "आवेदन शुल्क Rs. 600 है और अंतिम तिथि 15 October 2026 है। "
         "Admit Card परीक्षा से सात दिन पहले जारी होंगे।")

FONT = "/System/Library/Fonts/Kohinoor.ttc"
CSS = f"@font-face {{font-family: hi; src: url({FONT});}} * {{font-family: hi; font-size: 13px; line-height: 1.6;}}"


def page_doc(text):
    # insert_htmlbox shapes complex scripts (conjuncts, matras) via HarfBuzz; insert_text does not.
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_htmlbox(pymupdf.Rect(60, 60, 540, 780), f"<p>{text}</p>", css=CSS)
    return doc


def page_image(text, dpi):
    pix = page_doc(text)[0].get_pixmap(dpi=dpi)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()


def image_pdf(img, path):
    ok, png = cv2.imencode(".png", img)
    doc = pymupdf.open(); page = doc.new_page()
    page.insert_image(page.rect, stream=png.tobytes())
    doc.save(path)


rng = np.random.default_rng(11)
for name, text in [("hindi", HINDI), ("mixed", MIXED)]:
    page_doc(text).save(f"{name}_digital.pdf")
    image_pdf(rotate(page_image(text, 200), 1.5), f"{name}_clean_scan.pdf")

    img = page_image(text, 130).astype(np.float32)
    img = 80 + img * 0.6 + rng.normal(0, 14, img.shape)
    img = cv2.GaussianBlur(np.clip(img, 0, 255).astype(np.uint8), (3, 3), 0)
    mask = rng.random(img.shape[:2]); img[mask < 0.006] = 0
    image_pdf(rotate(img, -3), f"{name}_poor_scan.pdf")

    img = page_image(text, 200).astype(np.float32)
    h, w = img.shape[:2]
    img *= np.linspace(1.0, 0.5, w)[None, :, None] * np.array([0.85, 0.95, 1.0])
    image_pdf(rotate(np.clip(img, 0, 255).astype(np.uint8), 4), f"{name}_phone_photo.pdf")

    open(f"ground_truth_{name}.txt", "w").write(text)
print("hindi samples written")
