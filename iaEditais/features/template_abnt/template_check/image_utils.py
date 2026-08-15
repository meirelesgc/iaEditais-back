# Renderização de páginas de PDF em imagem PNG, sem dependência de Poppler
# (usa apenas PyMuPDF). Usado na verificação visual (ver visual_check.py).

from __future__ import annotations

from pathlib import Path

import pymupdf


def render_page_png(pdf_path: str, page_number: int = 1, dpi: int = 150) -> bytes:
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_number - 1]
        zoom = dpi / 72.0
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        return pixmap.tobytes('png')
    finally:
        doc.close()


def save_png(data: bytes, out_path: str) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(data)
    return out_path
