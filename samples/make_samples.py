"""Build synthetic test PDFs with known ground truth for each input type."""
import cv2
import numpy as np
import pymupdf

TEXT = ("The Rajasthan Public Service Commission conducts the State and Subordinate Services "
        "Combined Competitive Examination. Candidates must submit the application form before "
        "the last date, 15 October 2026, along with a fee of Rs. 600. Admit cards will be issued "
        "online seven days before the examination. The syllabus covers history, geography, polity, "
        "economy, science and current affairs of Rajasthan and India.")


def digital(path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(60, 60, 540, 780), TEXT, fontsize=12)
    doc.save(path)


def page_image(dpi=200):
    doc = pymupdf.open(); page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(60, 60, 540, 780), TEXT, fontsize=12)
    pix = page.get_pixmap(dpi=dpi)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()


def image_pdf(img, path):
    ok, png = cv2.imencode(".png", img)
    doc = pymupdf.open(); page = doc.new_page()
    page.insert_image(page.rect, stream=png.tobytes())
    doc.save(path)


def rotate(img, deg):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1)
    return cv2.warpAffine(img, m, (w, h), borderValue=(255, 255, 255))


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    digital("digital.pdf")
    image_pdf(rotate(page_image(200), 1.5), "clean_scan.pdf")

    # poor scan: low res, faded, salt-and-pepper noise, blur, 3 deg skew
    img = page_image(110).astype(np.float32)
    img = 90 + img * 0.55
    img += rng.normal(0, 18, img.shape)
    img = cv2.GaussianBlur(np.clip(img, 0, 255).astype(np.uint8), (3, 3), 0)
    mask = rng.random(img.shape[:2])
    img[mask < 0.01] = 0; img[mask > 0.99] = 255
    image_pdf(rotate(img, -3), "poor_scan.pdf")

    # phone photo: warm tint, strong lighting gradient + shadow band, 4 deg tilt
    img = page_image(200).astype(np.float32)
    h, w = img.shape[:2]
    grad = np.linspace(1.0, 0.45, w)[None, :, None] * np.linspace(1.0, 0.8, h)[:, None, None]
    img = img * grad
    img[int(h * .55):int(h * .7)] *= 0.6
    img *= np.array([0.85, 0.95, 1.0])
    image_pdf(rotate(np.clip(img, 0, 255).astype(np.uint8), 4), "phone_photo.pdf")

    open("ground_truth.txt", "w").write(TEXT)
    print("samples written")
