"""
Schema for State Opportunity Zone records.
"""

from datetime import date
from pydantic import BaseModel, field_validator


class OpportunityZoneRecord(BaseModel):
    """A single State Opportunity Zone designation."""
    
    area: str
    designated_date: date
    start_year: int
    end_year: int
    
    @field_validator("area")
    @classmethod
    def normalize_area(cls, v: str) -> str:
        """Clean up area name."""
        # Normalize whitespace and dashes
        v = " ".join(v.split())
        # Replace em-dashes and en-dashes with regular dashes
        v = v.replace("–", "-").replace("—", "-")
        return v.strip()
    
    @field_validator("start_year", "end_year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Ensure year is reasonable. Fix common typos like 3032 -> 2032."""
        # Fix typo: 3032 -> 2032, 3033 -> 2033, etc.
        if 3000 <= v <= 3050:
            v = v - 1000
        if not 2000 <= v <= 2050:
            raise ValueError(f"Year out of range: {v}")
        return v

