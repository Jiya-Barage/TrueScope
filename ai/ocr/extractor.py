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


def _group_words_into_lines(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group words into reading-order lines based on vertical position.

    Computes each word's vertical center (top + height / 2), sorts words by center,
    and starts a new line when a word's center differs from the current line's running
    mean center by more than ~0.6 * median_word_height. Then sorts words in each
    line by 'left' coordinate.

    Args:
        words: List of word dicts with 'text', 'conf', 'top', 'left', 'height'.

    Returns:
        List of line dicts: [{"text": str, "conf": float (0.0 to 1.0)}].
    """
    if not words:
        return []

    # Calculate median word height as baseline for clustering threshold
    valid_heights = [float(w.get("height", 10)) for w in words if float(w.get("height", 10)) > 0]
    if valid_heights:
        sorted_h = sorted(valid_heights)
        n = len(sorted_h)
        median_height = sorted_h[n // 2] if n % 2 != 0 else (sorted_h[n // 2 - 1] + sorted_h[n // 2]) / 2.0
    else:
        median_height = 15.0

    threshold = max(6.0, 0.6 * median_height)

    # Compute vertical center for each word
    enriched = []
    for w in words:
        top = float(w.get("top", 0))
        h = float(w.get("height", median_height))
        center_y = top + h / 2.0
        enriched.append({
            "word": w,
            "center_y": center_y,
            "left": float(w.get("left", 0)),
        })

    # Sort primarily by vertical center, secondarily by horizontal left position
    enriched.sort(key=lambda item: (item["center_y"], item["left"]))

    # Group into lines
    lines_clusters: List[Dict[str, Any]] = []
    for item in enriched:
        cy = item["center_y"]
        placed = False

        if lines_clusters:
            last_line = lines_clusters[-1]
            if abs(cy - last_line["mean_center"]) <= threshold:
                last_line["items"].append(item)
                # Update running mean center
                total_y = sum(x["center_y"] for x in last_line["items"])
                last_line["mean_center"] = total_y / len(last_line["items"])
                placed = True

        if not placed:
            lines_clusters.append({
                "mean_center": cy,
                "items": [item],
            })

    # For each cluster, sort words by left, join with single space, and compute mean conf
    result_lines: List[Dict[str, Any]] = []
    for cluster in lines_clusters:
        cluster_items = cluster["items"]
        cluster_items.sort(key=lambda x: x["left"])
        line_text = " ".join(x["word"]["text"].strip() for x in cluster_items if x["word"]["text"].strip())
        if not line_text:
            continue
        confs = [float(x["word"]["conf"]) for x in cluster_items if isinstance(x["word"].get("conf"), (int, float))]
        mean_conf = round(sum(confs) / len(confs), 4) if confs else 0.85
        result_lines.append({
            "text": line_text,
            "conf": mean_conf,
        })

    return result_lines


def _extract_from_image(
    image: Image.Image,
    page: int = 1,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Run OCR on a single PIL Image using pytesseract image_to_data.

    Groups words into lines by vertical position (top + height/2).

    Args:
        image: Input PIL Image.

    Returns:
        A tuple of (lines list, words list).
        lines is [{"text": str, "conf": float (0-1)}].
        words is [{"text": str, "conf": float (0-1)}].
    """
    processed = preprocess_image(image)
    data = pytesseract.image_to_data(processed, config="--psm 6", output_type=pytesseract.Output.DICT)

    words_with_geom: List[Dict[str, Any]] = []
    clean_words: List[Dict[str, Any]] = []

    num_entries = len(data.get("text", []))

    # Estimate baseline skew angle/slope across multi-word lines to normalize tilted scans
    line_word_pts: Dict[int, List[tuple[float, float]]] = {}
    for i in range(num_entries):
        raw_text = data["text"][i]
        token = raw_text.strip() if isinstance(raw_text, str) else ""
        if not token:
            continue
        try:
            if float(data["conf"][i]) < 0:
                continue
        except (ValueError, TypeError):
            continue
        ln = int(data.get("line_num", [0])[i])
        left = float(data.get("left", [0])[i])
        cy = float(data.get("top", [0])[i]) + float(data.get("height", [10])[i]) / 2.0
        line_word_pts.setdefault(ln, []).append((left, cy))

    slopes: List[float] = []
    for pts in line_word_pts.values():
        if len(pts) >= 2:
            pts.sort(key=lambda p: p[0])
            dx = pts[-1][0] - pts[0][0]
            if dx > 150:
                slopes.append((pts[-1][1] - pts[0][1]) / dx)

    median_slope = sorted(slopes)[len(slopes) // 2] if slopes else 0.0

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
        top = float(data.get("top", [0])[i])
        left = float(data.get("left", [0])[i])
        height = float(data.get("height", [10])[i])
        width = float(data.get("width", [10])[i])

        effective_top = top - median_slope * left

        word_obj = {
            "text": token,
            "conf": norm_conf,
            "top": effective_top,
            "left": left,
            "height": height,
            "width": width,
        }
        words_with_geom.append(word_obj)
        clean_words.append({"text": token, "conf": norm_conf})

    lines = _group_words_into_lines(words_with_geom)
    return lines, clean_words


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
