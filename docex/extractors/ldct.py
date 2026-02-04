"""
Extractor for Less Developed Census Tract (LDCT) PDFs.

These PDFs have a multi-column layout (typically 3 columns) organized by:
- MSA (Metropolitan Statistical Area) headers
- County names
- Census tract numbers

Each column must be processed independently to avoid mixing counties.
Supports both digital PDFs and scanned/image PDFs (via OCR).
"""

import re
from pathlib import Path
from dataclasses import dataclass

import fitz  # PyMuPDF

from ..schema.ldct import LDCTRecord
from ..utils.ocr import is_scanned_pdf, ocr_pdf, ocr_pdf_by_columns


@dataclass
class TextSpan:
    """A text span with position information."""
    text: str
    x: float
    y: float
    page: int


class LDCTExtractor:
    """Extract Less Developed Census Tract data from PDFs."""
    
    # Known Georgia MSA names (partial matches ok)
    KNOWN_MSAS = {
        "ALBANY": "ALBANY",
        "ATHENS": "ATHENS-CLARK",
        "ATLANTA": "ATLANTA-SANDY SPRINGS-ROSWELL",
        "AUGUSTA": "AUGUSTA-RICHMOND",
        "BRUNSWICK": "BRUNSWICK",
        "COLUMBUS": "COLUMBUS",
        "DALTON": "DALTON",
        "GAINESVILLE": "GAINESVILLE",
        "HINESVILLE": "HINESVILLE",
        "MACON": "MACON",
        "ROME": "ROME",
        "SAVANNAH": "SAVANNAH",
        "VALDOSTA": "VALDOSTA",
        "WARNER": "WARNER ROBINS",
    }
    
    # Pattern for census tracts
    TRACT_PATTERN = re.compile(r"Census Tract\s+(\d+(?:\.\d+)?)", re.IGNORECASE)
    
    # Pattern for "(cont.)" suffix
    CONT_PATTERN = re.compile(r"\s*\(cont\.?\)\s*$", re.IGNORECASE)
    
    def __init__(self):
        self.records: list[LDCTRecord] = []
    
    def extract_year_from_filename(self, filepath: Path) -> int:
        """Extract year from filename."""
        filename = filepath.stem.lower()
        match = re.search(r"20[12]\d", filename)
        if match:
            return int(match.group())
        raise ValueError(f"Could not extract year from filename: {filepath.name}")
    
    def extract_text_spans(self, doc: fitz.Document) -> list[TextSpan]:
        """Extract all text spans with positions from the document."""
        spans = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:  # Skip non-text blocks
                    continue
                
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        x = span["bbox"][0]
                        y = span["bbox"][1]
                        text = span.get("text", "").strip()
                        
                        if text:
                            spans.append(TextSpan(
                                text=text,
                                x=x,
                                y=y,
                                page=page_num
                            ))
        
        return spans
    
    def detect_columns(self, spans: list[TextSpan]) -> list[float]:
        """Detect column x-positions from text spans."""
        from collections import Counter
        
        # Round x-coords and count occurrences
        x_counts = Counter(round(s.x / 10) * 10 for s in spans)
        
        # Find significant column positions (more than 5 items)
        columns = sorted([x for x, count in x_counts.items() if count > 5])
        
        # Merge columns that are too close (within 30 units)
        merged = []
        for x in columns:
            if not merged or x - merged[-1] > 30:
                merged.append(x)
        
        return merged
    
    def assign_to_column(self, x: float, columns: list[float]) -> int:
        """Assign an x-coordinate to the nearest column index."""
        min_dist = float("inf")
        best_col = 0
        for i, col_x in enumerate(columns):
            dist = abs(x - col_x)
            if dist < min_dist:
                min_dist = dist
                best_col = i
        return best_col
    
    def is_msa_header(self, text: str) -> str | None:
        """Check if text is an MSA header, return normalized MSA name or None."""
        text = text.strip()
        text_upper = text.upper()
        
        # Remove (cont.) suffix
        text_upper = self.CONT_PATTERN.sub("", text_upper)
        
        # Check against known MSA prefixes
        for prefix, full_name in self.KNOWN_MSAS.items():
            if prefix in text_upper:
                return full_name
        
        # Check if ends with MSA
        if text_upper.endswith("MSA"):
            return text_upper[:-3].strip().rstrip("-").strip()
        
        return None
    
    # Common OCR corrections for county names
    COUNTY_CORRECTIONS = {
        "dekalb cer": "DeKalb",
        "dekalb": "DeKalb",
        "mcintosh": "McIntosh",
        "mcduffie": "McDuffie",
        "aker": "Baker",  # OCR cut-off
    }
    
    def is_county_name(self, text: str) -> str | None:
        """Check if text is a county name, return normalized name or None."""
        text = text.strip()
        
        # Remove (cont.) suffix
        text = self.CONT_PATTERN.sub("", text)
        
        # Apply OCR corrections
        text_lower = text.lower()
        if text_lower in self.COUNTY_CORRECTIONS:
            return self.COUNTY_CORRECTIONS[text_lower]
        
        # Check for partial matches in corrections (e.g., "Dekalb Cer" contains "dekalb")
        for wrong, correct in self.COUNTY_CORRECTIONS.items():
            if wrong in text_lower:
                return correct
        
        # Skip if it's a tract
        if "census tract" in text.lower():
            return None
        
        # Skip if it's page info or header
        if text.isdigit() or text.startswith("Page"):
            return None
        if "Less Developed" in text or "Annual Census" in text or "O.C.G.A" in text:
            return None
        if "MSA" in text.upper():
            return None
        if text.upper() in ["SPRINGS-ROSWELL", "SPRINGS", "ROSWELL"]:
            return None
        
        # Should be 1-2 words, start with uppercase
        words = text.split()
        if len(words) > 2:
            return None
        
        if not text or not text[0].isupper():
            return None
        
        # Must be mostly letters
        if re.match(r"^[A-Z][a-zA-Z\s]+$", text):
            return text.title()
        
        return None
    
    def extract_from_ocr_column(self, text: str, year: int, current_msa: str | None = None) -> tuple[list[LDCTRecord], str | None]:
        """
        Extract records from a single column's OCR text.
        
        Args:
            text: OCR text from one column
            year: Year for records
            current_msa: Starting MSA context (from previous column/page)
        
        Returns:
            Tuple of (records, final_msa) - final_msa to carry over to next column
        """
        records = []
        current_county = None
        
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip headers and footers
            if "Page" in line and "of" in line:
                continue
            if "Appendix" in line:
                continue
            if "Less Developed" in line or "Annual Census" in line:
                continue
            if "O.C.G.A" in line:
                continue
            if line.startswith("20") and "Census" not in line:
                continue
            
            # Check for MSA header
            msa = self.is_msa_header(line)
            if msa:
                current_msa = msa
                current_county = None
                continue
            
            # Check for census tract
            tract_match = self.TRACT_PATTERN.search(line)
            if tract_match:
                tract = tract_match.group(1)
                if current_msa and current_county:
                    try:
                        record = LDCTRecord(
                            year=year,
                            msa=current_msa,
                            county=current_county,
                            tract=tract
                        )
                        records.append(record)
                    except ValueError:
                        pass
                continue
            
            # Check for county name
            county = self.is_county_name(line)
            if county:
                current_county = county
        
        return records, current_msa
    
    def extract(self, filepath: str | Path, use_ocr: bool | None = None) -> list[LDCTRecord]:
        """
        Extract all LDCT records from a PDF file.
        
        Args:
            filepath: Path to PDF file
            use_ocr: Force OCR on/off. If None, auto-detect based on PDF type.
        """
        filepath = Path(filepath)
        year = self.extract_year_from_filename(filepath)
        
        # Check if we need OCR
        if use_ocr is None:
            use_ocr = is_scanned_pdf(filepath)
        
        if use_ocr:
            print(f"  Using OCR for scanned PDF (column-aware)...")
            
            # First, get full-page OCR to extract MSA headers
            pages_text = ocr_pdf(filepath, dpi=150)
            
            # Extract MSA sequence from full pages
            page_msas = []
            for page_text in pages_text:
                msas_in_page = []
                for line in page_text.split("\n"):
                    msa = self.is_msa_header(line)
                    if msa:
                        msas_in_page.append(msa)
                page_msas.append(msas_in_page)
            
            # Now get column-separated OCR
            pages_columns = ocr_pdf_by_columns(filepath, num_columns=3, dpi=150)
            
            self.records = []
            global_msa = None
            msa_idx = 0  # Track which MSA we're on
            
            for page_num, columns in enumerate(pages_columns):
                # Get MSAs for this page (if any)
                current_page_msas = page_msas[page_num] if page_num < len(page_msas) else []
                
                # Use first MSA on page if we don't have one
                if current_page_msas and global_msa is None:
                    global_msa = current_page_msas[0]
                
                for col_idx, col_text in enumerate(columns):
                    col_records, new_msa = self.extract_from_ocr_column(
                        col_text, year, current_msa=global_msa
                    )
                    self.records.extend(col_records)
                    
                    # Update global MSA if column found one
                    if new_msa and new_msa != global_msa:
                        global_msa = new_msa
            
            return self.records
        
        # Digital PDF - use position-based extraction
        doc = fitz.open(filepath)
        spans = self.extract_text_spans(doc)
        doc.close()
        
        # Detect columns
        columns = self.detect_columns(spans)
        
        # Group spans by page and column
        from collections import defaultdict
        page_columns = defaultdict(lambda: defaultdict(list))
        
        for span in spans:
            col = self.assign_to_column(span.x, columns)
            page_columns[span.page][col].append(span)
        
        # Sort each column by y-coordinate
        for page in page_columns:
            for col in page_columns[page]:
                page_columns[page][col].sort(key=lambda s: s.y)
        
        # Track MSA state globally (carries across pages and columns)
        # But county state is per-column
        global_msa = None
        
        self.records = []
        
        # Process pages in order
        for page_num in sorted(page_columns.keys()):
            # Process columns left to right
            for col_idx in sorted(page_columns[page_num].keys()):
                col_spans = page_columns[page_num][col_idx]
                
                current_msa = global_msa
                current_county = None
                
                for span in col_spans:
                    text = span.text
                    
                    # Check for MSA header
                    msa = self.is_msa_header(text)
                    if msa:
                        current_msa = msa
                        global_msa = msa
                        current_county = None  # Reset county on new MSA
                        continue
                    
                    # Check for census tract
                    tract_match = self.TRACT_PATTERN.search(text)
                    if tract_match:
                        tract = tract_match.group(1)
                        if current_msa and current_county:
                            try:
                                record = LDCTRecord(
                                    year=year,
                                    msa=current_msa,
                                    county=current_county,
                                    tract=tract
                                )
                                self.records.append(record)
                            except ValueError as e:
                                print(f"Warning: Invalid record - {e}")
                        continue
                    
                    # Check for county name
                    county = self.is_county_name(text)
                    if county:
                        current_county = county
        
        return self.records
    
    def to_dict(self) -> dict:
        """Convert records to a nested dictionary format: {year: {msa: {county: [tracts]}}}."""
        result = {}
        for record in self.records:
            year_key = str(record.year)
            if year_key not in result:
                result[year_key] = {}
            
            msa_key = record.msa
            if msa_key not in result[year_key]:
                result[year_key][msa_key] = {}
            
            county_key = record.county
            if county_key not in result[year_key][msa_key]:
                result[year_key][msa_key][county_key] = []
            
            if record.tract not in result[year_key][msa_key][county_key]:
                result[year_key][msa_key][county_key].append(record.tract)
        
        # Sort tracts numerically
        for year in result:
            for msa in result[year]:
                for county in result[year][msa]:
                    result[year][msa][county].sort(
                        key=lambda x: (float(x.split(".")[0]), float(x.split(".")[-1]) if "." in x else 0)
                    )
        
        return result
    
    def to_simple_dict(self) -> dict:
        """Convert records to simpler format: {year: {county: [tracts]}}."""
        result = {}
        for record in self.records:
            year_key = str(record.year)
            if year_key not in result:
                result[year_key] = {}
            
            county_key = record.county
            if county_key not in result[year_key]:
                result[year_key][county_key] = []
            
            if record.tract not in result[year_key][county_key]:
                result[year_key][county_key].append(record.tract)
        
        # Sort tracts
        for year in result:
            for county in result[year]:
                result[year][county].sort(
                    key=lambda x: (float(x.split(".")[0]), float(x.split(".")[-1]) if "." in x else 0)
                )
        
        return result
    
    def to_flat_list(self) -> list[dict]:
        """Convert records to a flat list of dicts."""
        return [record.model_dump() for record in self.records]
