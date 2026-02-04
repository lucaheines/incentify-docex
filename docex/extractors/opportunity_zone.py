"""
Extractor for State Opportunity Zone PDFs.

These PDFs have a table format where each column is on separate lines:
- Designated Area name (one or more lines)
- Date Designated (one line)
- Designation Period (one or two lines)

Example:
    Acworth
    March 5, 2021
    2021 through 2030
"""

import re
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

from ..schema.opportunity_zone import OpportunityZoneRecord


class OpportunityZoneExtractor:
    """Extract State Opportunity Zone data from PDFs."""
    
    MONTH_MAP = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    # Date pattern: Month DD, YYYY
    DATE_PATTERN = re.compile(r"^([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})$")
    
    # Period pattern: YYYY through YYYY
    PERIOD_PATTERN = re.compile(r"(\d{4})\s+(?:through|though)\s+(\d{4})", re.IGNORECASE)
    
    def __init__(self):
        self.records: list[OpportunityZoneRecord] = []
    
    def parse_date(self, date_str: str) -> date | None:
        """Parse date string like 'March 5, 2021' to date object."""
        match = self.DATE_PATTERN.match(date_str.strip())
        if not match:
            return None
        
        month_name = match.group(1).lower()
        day = int(match.group(2))
        year = int(match.group(3))
        month = self.MONTH_MAP.get(month_name)
        
        if not month:
            return None
        
        return date(year, month, day)
    
    def parse_period(self, period_str: str) -> tuple[int, int] | None:
        """Parse period like '2021 through 2030' to (start_year, end_year)."""
        match = self.PERIOD_PATTERN.search(period_str)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None
    
    def extract(self, filepath: str | Path) -> list[OpportunityZoneRecord]:
        """Extract all Opportunity Zone records from a PDF file."""
        filepath = Path(filepath)
        
        doc = fitz.open(filepath)
        self.records = []
        
        # Collect all lines from all pages
        all_lines = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            all_lines.extend(text.split("\n"))
        
        doc.close()
        
        # Filter and clean lines
        lines = []
        for line in all_lines:
            line = line.strip()
            if not line:
                continue
            # Skip headers and footers
            if "Updated as of" in line:
                continue
            if line.startswith("Page ") and " of " in line:
                continue
            if "STATE OPPORTUNITY ZONE" in line:
                continue
            if "O.C.G.A" in line:
                continue
            if "Designated Area" in line and "Date" in line:
                continue
            if "Designated Area *" in line or "Date Designated" in line or "Designation Period" in line:
                continue
            if line.startswith("*"):
                continue
            if "https://" in line:
                continue
            if "within or adjacent" in line or "greater as determined" in line:
                continue
            if "included within" in line or "has been adopted" in line:
                continue
            if "community affairs" in line or "Designations made" in line:
                continue
            if "poverty rate" in line or "census block" in line:
                continue
            if "displays pervasive" in line:
                continue
            
            lines.append(line)
        
        # Process lines in groups
        # Pattern: Area (1+ lines), Date (1 line), Period (1-2 lines)
        i = 0
        while i < len(lines):
            # Try to identify what this line is
            line = lines[i]
            
            # Check if it's a date
            date_val = self.parse_date(line)
            if date_val:
                i += 1
                continue
            
            # Check if it's a period
            period = self.parse_period(line)
            if period:
                i += 1
                continue
            
            # Must be an area name - collect until we find a date
            area_parts = [line]
            j = i + 1
            
            while j < len(lines):
                next_line = lines[j]
                # Check if next line is a date
                if self.parse_date(next_line):
                    break
                # Could be continuation of area or partial date line
                if next_line.startswith("amended") or "and" in next_line.lower():
                    area_parts.append(next_line)
                    j += 1
                    continue
                # Check if it looks like a period start
                if self.parse_period(next_line):
                    break
                # Otherwise it's part of the area
                area_parts.append(next_line)
                j += 1
            
            # Now j points to the date line (hopefully)
            if j >= len(lines):
                break
            
            date_line = lines[j]
            date_val = self.parse_date(date_line)
            
            if not date_val:
                # Try combining with next line if it has "and amended"
                if j + 1 < len(lines) and ("amended" in lines[j].lower() or "and" in lines[j].lower()):
                    # Skip this weird date format and try the next line
                    j += 1
                    if j < len(lines):
                        date_line = lines[j]
                        date_val = self.parse_date(date_line)
            
            if not date_val:
                i = j + 1
                continue
            
            # Now look for period
            k = j + 1
            period_str = ""
            
            while k < len(lines) and not self.parse_period(period_str):
                period_str += " " + lines[k]
                period_str = period_str.strip()
                
                # Check if we've gone too far (hit another area)
                if k + 1 < len(lines):
                    next_next = lines[k + 1]
                    if self.parse_date(next_next):
                        break
                
                period = self.parse_period(period_str)
                if period:
                    break
                k += 1
            
            period = self.parse_period(period_str)
            
            if period:
                area = " ".join(area_parts)
                # Clean up area name
                area = " ".join(area.split())
                area = area.replace("–", "-").replace("—", "-")
                
                try:
                    record = OpportunityZoneRecord(
                        area=area,
                        designated_date=date_val,
                        start_year=period[0],
                        end_year=period[1]
                    )
                    self.records.append(record)
                except ValueError as e:
                    print(f"Warning: Could not create record - {e}")
            
            i = k + 1
        
        return self.records
    
    def to_dict(self) -> list[dict]:
        """Convert records to a list of dicts."""
        return [
            {
                "area": r.area,
                "designated_date": r.designated_date.isoformat(),
                "start_year": r.start_year,
                "end_year": r.end_year
            }
            for r in self.records
        ]
    
    def to_flat_list(self) -> list[dict]:
        """Convert records to a flat list of dicts."""
        return self.to_dict()
