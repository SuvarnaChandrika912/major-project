import logging
import shutil
from functools import lru_cache
from pathlib import Path

from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

_WINDOWS_DEFAULT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


@lru_cache
def tesseract_available() -> bool:
    try:
        import pytesseract
    except ImportError:
        return False
    cmd = settings.TESSERACT_CMD or shutil.which("tesseract") or (str(_WINDOWS_DEFAULT) if _WINDOWS_DEFAULT.exists() else "")
    if not cmd:
        return False
    pytesseract.pytesseract.tesseract_cmd = cmd
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001
        return False


def ocr_image(image: Image.Image, languages: str | None = None) -> str:
    if not tesseract_available():
        raise RuntimeError(
            "Tesseract OCR is not installed or TESSERACT_CMD is not configured; scanned pages cannot be read."
        )
    import pytesseract

    gray = image.convert("L")
    return pytesseract.image_to_string(gray, lang=languages or settings.OCR_LANGUAGES, config="--psm 3")
