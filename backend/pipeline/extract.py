"""Hybrid PDF extraction with PyMuPDF (fitz).

For each page: if it carries enough selectable text we keep the text (cheap and
exact); otherwise we rasterise the page to a PNG so a vision model can read the
scan. No poppler / system dependency required.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass

import fitz  # PyMuPDF

from config import (
    IMAGE_QUALITY,
    MAX_IMAGE_PX,
    MAX_PAGES,
    MIN_TEXT_CHARS_PER_PAGE,
    RENDER_DPI,
)


@dataclass
class PageContent:
    page_number: int
    kind: str  # "text" or "image"
    text: str | None = None
    image_b64: str | None = None  # JPEG, base64 (no data-uri prefix)

    def data_uri(self) -> str | None:
        if self.image_b64 is None:
            return None
        return f"data:image/jpeg;base64,{self.image_b64}"


def _render_jpeg_b64(page) -> str:
    """Rasterise a page to a size-capped JPEG, returned as base64.

    Uses the configured DPI but downscales so the longest side never exceeds
    MAX_IMAGE_PX, keeping the payload small enough for the API while remaining
    legible for the vision model.
    """
    rect = page.rect
    longest_pt = max(rect.width, rect.height) or 1
    dpi_zoom = RENDER_DPI / 72.0
    cap_zoom = MAX_IMAGE_PX / longest_pt
    zoom = min(dpi_zoom, cap_zoom)
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    jpeg = pix.tobytes("jpeg", jpg_quality=IMAGE_QUALITY)
    return base64.b64encode(jpeg).decode("ascii")


def extract_pages(pdf_bytes: bytes) -> list[PageContent]:
    """Return per-page content, choosing text vs image per page."""
    pages: list[PageContent] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            if i >= MAX_PAGES:
                break
            text = page.get_text("text").strip()
            if len(text) >= MIN_TEXT_CHARS_PER_PAGE:
                pages.append(PageContent(page_number=i + 1, kind="text", text=text))
            else:
                img_b64 = _render_jpeg_b64(page)
                pages.append(
                    PageContent(page_number=i + 1, kind="image", image_b64=img_b64)
                )
    return pages
