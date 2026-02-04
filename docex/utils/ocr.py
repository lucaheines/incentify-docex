"""
OCR utilities for processing scanned PDFs.
"""

import io
from pathlib import Path

import fitz  # PyMuPDF


def is_scanned_pdf(filepath: str | Path) -> bool:
    """Check if a PDF is scanned (image-based) vs digital text."""
    doc = fitz.open(filepath)
    
    # Check first few pages
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        text = page.get_text().strip()
        
        # If we get substantial text, it's digital
        if len(text) > 100:
            doc.close()
            return False
    
    doc.close()
    return True


def ocr_pdf_page(page: fitz.Page, dpi: int = 150) -> str:
    """
    Run OCR on a single PDF page.
    
    Args:
        page: PyMuPDF page object
        dpi: Resolution for rendering (higher = better OCR but slower)
    
    Returns:
        Extracted text from OCR
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise ImportError("OCR requires pytesseract and Pillow: pip install pytesseract pillow")
    
    # Render page as image
    pix = page.get_pixmap(dpi=dpi)
    
    # Convert to PIL Image
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Run OCR
    text = pytesseract.image_to_string(img)
    
    return text


def ocr_pdf_page_columns(page: fitz.Page, num_columns: int = 3, dpi: int = 150) -> list[str]:
    """
    Run OCR on a PDF page, extracting each column separately.
    
    Args:
        page: PyMuPDF page object
        num_columns: Number of columns to split the page into
        dpi: Resolution for rendering
    
    Returns:
        List of text strings, one per column (left to right)
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise ImportError("OCR requires pytesseract and Pillow: pip install pytesseract pillow")
    
    # Render page as image
    pix = page.get_pixmap(dpi=dpi)
    
    # Convert to PIL Image
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    width, height = img.size
    col_width = width // num_columns
    
    column_texts = []
    
    for i in range(num_columns):
        # Calculate column boundaries with slight overlap
        left = max(0, i * col_width - 5)
        right = min(width, (i + 1) * col_width + 5)
        
        # Crop to this column
        col_img = img.crop((left, 0, right, height))
        
        # OCR this column
        text = pytesseract.image_to_string(col_img)
        column_texts.append(text)
    
    return column_texts


def ocr_pdf(filepath: str | Path, dpi: int = 150) -> list[str]:
    """
    Run OCR on all pages of a PDF.
    
    Args:
        filepath: Path to PDF file
        dpi: Resolution for rendering
    
    Returns:
        List of text strings, one per page
    """
    doc = fitz.open(filepath)
    pages_text = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = ocr_pdf_page(page, dpi=dpi)
        pages_text.append(text)
    
    doc.close()
    return pages_text


def ocr_pdf_by_columns(filepath: str | Path, num_columns: int = 3, dpi: int = 150) -> list[list[str]]:
    """
    Run OCR on all pages of a PDF, extracting columns separately.
    
    Args:
        filepath: Path to PDF file
        num_columns: Number of columns per page
        dpi: Resolution for rendering
    
    Returns:
        List of pages, each containing a list of column texts
    """
    doc = fitz.open(filepath)
    pages_columns = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        columns = ocr_pdf_page_columns(page, num_columns=num_columns, dpi=dpi)
        pages_columns.append(columns)
    
    doc.close()
    return pages_columns
