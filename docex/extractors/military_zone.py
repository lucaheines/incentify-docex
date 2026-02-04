"""
Extractor for Military Zone PDFs.

These PDFs have a tabular format with:
- County name
- Census tract number
- Designation effective date

Example:
    Bryan    9203.01    Designation effective January 1, 2024
"""

import re
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

from ..schema.military_zone import MilitaryZoneRecord


class MilitaryZoneExtractor:
    """Extract Military Zone data from PDFs."""
    
    # Pattern for extracting county, tract, and date from a line
    ROW_PATTERN = re.compile(
        r"([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+"  # County name
        r"(\d+\.\d{2})\s+"                   # Tract number (e.g., 9203.01)
        r"Designation effective\s+"          # Label
        r"(\w+\s+\d{1,2},\s+\d{4})",         # Date (e.g., January 1, 2024)
        re.IGNORECASE
    )
    
    MONTH_MAP = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    def __init__(self):
        self.records: list[MilitaryZoneRecord] = []
    
    def extract_year_from_filename(self, filepath: Path) -> int:
        """Extract year from filename."""
        filename = filepath.stem.lower()
        match = re.search(r"20[12]\d", filename)
        if match:
            return int(match.group())
        raise ValueError(f"Could not extract year from filename: {filepath.name}")
    
    def parse_date(self, date_str: str) -> date:
        """Parse date string like 'January 1, 2024' to date object."""
        parts = date_str.replace(",", "").split()
        month_name = parts[0].lower()
        day = int(parts[1])
        year = int(parts[2])
        month = self.MONTH_MAP.get(month_name, 1)
        return date(year, month, day)
    
    def extract(self, filepath: str | Path) -> list[MilitaryZoneRecord]:
        """Extract all Military Zone records from a PDF file."""
        filepath = Path(filepath)
        year = self.extract_year_from_filename(filepath)
        
        doc = fitz.open(filepath)
        self.records = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Find all matches in the page
            for match in self.ROW_PATTERN.finditer(text):
                county = match.group(1).strip()
                tract = match.group(2)
                date_str = match.group(3)
                
                try:
                    effective_date = self.parse_date(date_str)
                    record = MilitaryZoneRecord(
                        year=year,
                        county=county,
                        tract=tract,
                        effective_date=effective_date
                    )
                    self.records.append(record)
                except (ValueError, KeyError) as e:
                    print(f"Warning: Could not parse record - {e}")
        
        doc.close()
        return self.records
    
    def to_dict(self) -> dict:
        """Convert records to a nested dictionary format."""
        result = {}
        for record in self.records:
            year_key = str(record.year)
            if year_key not in result:
                result[year_key] = {}
            
            county_key = record.county
            if county_key not in result[year_key]:
                result[year_key][county_key] = []
            
            result[year_key][county_key].append({
                "tract": record.tract,
                "effective_date": record.effective_date.isoformat()
            })
        
        return result
    
    def to_flat_list(self) -> list[dict]:
        """Convert records to a flat list of dicts."""
        return [
            {
                "year": r.year,
                "county": r.county,
                "tract": r.tract,
                "effective_date": r.effective_date.isoformat()
            }
            for r in self.records
        ]

