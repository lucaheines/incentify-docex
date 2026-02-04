"""
Schema for Military Zone records.
"""

from datetime import date
from pydantic import BaseModel, field_validator
import re


class MilitaryZoneRecord(BaseModel):
    """A single Military Zone census tract designation."""
    
    year: int
    county: str
    tract: str
    effective_date: date
    
    @field_validator("tract")
    @classmethod
    def validate_tract(cls, v: str) -> str:
        """Ensure tract is a valid format (digits with optional decimal)."""
        if not re.match(r"^\d+(\.\d+)?$", v):
            raise ValueError(f"Invalid tract format: {v}")
        return v
    
    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Ensure year is reasonable."""
        if not 2000 <= v <= 2030:
            raise ValueError(f"Year out of range: {v}")
        return v
    
    @field_validator("county")
    @classmethod
    def normalize_county(cls, v: str) -> str:
        """Normalize county name to title case."""
        return v.strip().title()

