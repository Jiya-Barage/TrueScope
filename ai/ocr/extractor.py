"""OCR extraction module for TrueScope.

Extracts text, word-level confidence scores, and page counts from PDF documents
and image files (PNG, JPG, JPEG) using pytesseract and pdf2image.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from PIL import Image, ImageOps
import pytesseract

# Load environment variables from .env file if present
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv()

# Configure Tesseract binary path if specified in environment or default install
TESSERACT_CMD = os.getenv("TESSERACT_CMD")
if not TESSERACT_CMD and os.path.isfile(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
    TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Configure Poppler binaries directory if specified in environment or default install
POPPLER_PATH = os.getenv("POPPLER_PATH")
if not POPPLER_PATH and os.path.isdir(r"C:\poppler\poppler-24.08.0\Library\bin"):
    POPPLER_PATH = r"C:\poppler\poppler-24.08.0\Library\bin"

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess an image for OCR by converting to grayscale and applying autocontrast.

    Args:
        image: Original PIL Image.

    Returns:
        Preprocessed PIL Image optimized for OCR legibility.
    """
    # Convert to 8-bit grayscale
    grayscale = image.convert("L")
    # Maximize image contrast
    return ImageOps.autocontrast(grayscale)


def _extract_from_image(
    image: Image.Image, page: int = 1
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Run OCR on a single PIL Image using pytesseract image_to_data.

    Groups words into lines by (page, block_num, par_num, line_num).

    Args:
        image: Input PIL Image.
        page: Page number index (1-based).

    Returns:
        A tuple of (lines list, words list).
        lines is [{"text": str, "conf": float (0-1)}].
        words is [{"text": str, "conf": float (0-1)}].
    """
    processed = preprocess_image(image)
    data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)

    words: List[Dict[str, Any]] = []
    line_groups: Dict[tuple[int, int, int, int], List[Dict[str, Any]]] = {}

    num_entries = len(data.get("text", []))
    for i in range(num_entries):
        raw_text = data["text"][i]
        token = raw_text.strip() if isinstance(raw_text, str) else ""
        if not token:
            continue

        try:
            raw_conf = float(data["conf"][i])
        except (ValueError, TypeError):
            continue

        # pytesseract returns -1 for layout/empty blocks
        if raw_conf < 0:
            continue

        # Normalise confidence from [0, 100] to [0.0, 1.0]
        norm_conf = max(0.0, min(1.0, round(raw_conf / 100.0, 4)))
        word_obj = {"text": token, "conf": norm_conf}
        words.append(word_obj)

        block_num = int(data.get("block_num", [0])[i])
        par_num = int(data.get("par_num", [0])[i])
        line_num = int(data.get("line_num", [0])[i])
        key = (page, block_num, par_num, line_num)

        if key not in line_groups:
            line_groups[key] = []
        line_groups[key].append(word_obj)

    lines: List[Dict[str, Any]] = []
    for _key, line_words in line_groups.items():
        if not line_words:
            continue
        line_str = " ".join(w["text"] for w in line_words)
        mean_conf = round(sum(w["conf"] for w in line_words) / len(line_words), 4)
        lines.append({"text": line_str, "conf": mean_conf})

    return lines, words


def extract(path: str) -> Dict[str, Any]:
    """Extract text, lines, word confidence scores, and page count from an invoice file.

    Supports PDF (via pdf2image) and standard image formats (.png, .jpg, .jpeg).

    Args:
        path: File system path to the document or image.

    Returns:
        A dictionary with:
            - "text" (str): Full text with lines joined by "\n".
            - "lines" (list[dict]): List of {"text": str, "conf": float (0.0 to 1.0)}.
            - "words" (list[dict]): List of {"text": str, "conf": float (0.0 to 1.0)}.
            - "pages" (int): Total number of pages processed.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file extension is not supported.
    """
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(f"Invoice file not found: {path}")

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Convert PDF or load image into a list of PIL Images
    if ext == ".pdf":
        try:
            from pdf2image import convert_from_path
        except ImportError as exc:
            raise ImportError("pdf2image is required to process PDF files.") from exc

        images = convert_from_path(str(file_path), poppler_path=POPPLER_PATH)
    else:
        with Image.open(file_path) as img:
            # Copy image to memory so the file handle can close
            images = [img.copy()]

    all_lines: List[Dict[str, Any]] = []
    all_words: List[Dict[str, Any]] = []

    for page_idx, image in enumerate(images, start=1):
        lines, words = _extract_from_image(image, page=page_idx)
        all_lines.extend(lines)
        all_words.extend(words)

    full_text = "\n".join(l["text"] for l in all_lines)

    return {
        "text": full_text,
        "lines": all_lines,
        "words": all_words,
        "pages": len(images),
    }
