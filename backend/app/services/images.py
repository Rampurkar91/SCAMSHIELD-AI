import io, os, warnings
from urllib.parse import urlsplit, parse_qs
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException
from .analysis import enrich

MAX_IMAGE_BYTES = 5 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 12_000_000


def decode_image(raw, mime):
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image exceeds 5 MiB.")
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Use a JPEG, PNG or WebP image.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(raw))
            actual = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
            }.get(image.format)
            if actual != mime:
                raise HTTPException(
                    415, "The image contents do not match its declared MIME type."
                )
            if image.width * image.height > 12_000_000:
                raise HTTPException(413, "Image exceeds 12 megapixels.")
            image.load()
            return image.convert("RGB")
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise HTTPException(422, "Invalid, corrupted or oversized image.")


def analyze_image(raw, mime, qr_only=False):
    image = decode_image(raw, mime)
    import cv2
    import numpy as np

    # Bounded pixel count, no external navigation, no original image retention.
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(
        cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    )
    text = ""
    ocr_status = "not_requested"
    if not qr_only:
        import pytesseract

        if os.getenv("TESSERACT_CMD"):
            pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
        try:
            text = pytesseract.image_to_string(
                image, lang=os.getenv("OCR_LANG", "eng"), timeout=15
            ).strip()
            ocr_status = "ok"
        except (
            pytesseract.TesseractNotFoundError,
            pytesseract.TesseractError,
            RuntimeError,
        ):
            ocr_status = "unavailable"
    if not text and not decoded:
        if ocr_status == "unavailable":
            raise HTTPException(
                503,
                "OCR is unavailable. Install Tesseract and the selected language data, or try a QR code image.",
            )
        raise HTTPException(
            422, "No readable text or QR payload was detected. Try a clearer image."
        )
    content = (text + "\n" + decoded).strip()[:12000]
    result = enrich("message", content)
    result["details"].update(
        extracted_text=text[:12000], qr_payload=decoded[:12000], ocr_status=ocr_status
    )
    if decoded:
        parsed = urlsplit(decoded)
        if parsed.scheme.lower() == "upi":
            fields = parse_qs(parsed.query)
            result["details"]["payment_intent"] = {
                "action": "Authorizing a payment, not receiving money",
                "payee": fields.get("pa", ["Not supplied"])[0][:200],
                "amount": fields.get("am", ["Not supplied"])[0][:50],
            }
        elif parsed.scheme in ("http", "https"):
            result["details"]["qr_type"] = "URL; not opened"
        else:
            result["details"]["qr_type"] = "Other payload; not executed"
    result["limitations"].append(
        "OCR may misread text. Screenshot analysis cannot prove a payment occurred or identify image manipulation reliably. Verify in your own official payment app."
    )
    return content, result
