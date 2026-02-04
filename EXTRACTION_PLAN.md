# Georgia Zone/Census Tract Extraction Plan

## Overview

This plan outlines the extraction strategy for three distinct types of Georgia tax incentive zone data:

1. **Less Developed Census Tracts (LDCT)** - County → Census Tract mappings
2. **Military Zones (MZ)** - County → Census Tract + Designation Date mappings  
3. **State Opportunity Zones (OZ)** - Named Area → Date + Period (no census tracts)

Each folder contains multiple PDFs spanning different years, requiring year-aware extraction.

---

## Data Structures

### 1. Less Developed Census Tracts (`GA_less_dev_cencus/`)

**Source Format:** Multi-column layout, organized by MSA (Metropolitan Statistical Area), then County, then Census Tracts

**Sample Raw Text:**
```
ALBANY MSA
Lee
Census Tract 202
Census Tract 203
Worth
Census Tract 9501
Census Tract 9502
```

**Target Schema:**
```python
@dataclass
class LDCTRecord:
    year: int                    # Extracted from filename/title (e.g., 2022)
    msa: str                     # e.g., "ALBANY", "ATLANTA-SANDY SPRINGS-ROSWELL"
    county: str                  # e.g., "Lee", "Fulton" (normalized, title case)
    tract: str                   # e.g., "202", "9501", "308.01" (NO "Census Tract" prefix)
```

**Output Example:**
```json
[
  {"year": 2022, "msa": "ALBANY", "county": "Lee", "tract": "202"},
  {"year": 2022, "msa": "ALBANY", "county": "Lee", "tract": "203"},
  {"year": 2022, "msa": "ALBANY", "county": "Worth", "tract": "9501"}
]
```

**Lookup-Friendly Alternative (grouped by county):**
```json
{
  "2022": {
    "ALBANY": {
      "Lee": ["202", "203"],
      "Worth": ["9501", "9502", "9505"]
    },
    "ATLANTA-SANDY SPRINGS-ROSWELL": {
      "Bartow": ["9602"],
      "Carroll": ["9101.01", "9103", "9105.01", "9105.02", "9108", "9109", "9112"],
      "Fulton": ["7", "10.02", "19", "21", "23", "24", "25", "26", "28", "..."]
    }
  }
}
```

**Files to Process:**
- `less_development_census_tracts_2020_0_2.pdf` → year: 2020
- `appendix_b_-_2021_ldct_designations_12-22-20.pdf` → year: 2021
- `3d_final_2022_ldcts.pdf` → year: 2022
- `appendix_b_final_2023_ldcts.pdf` → year: 2023
- `appendix_b_final_2024_ldcts.pdf` → year: 2024

---

### 2. Military Zones (`GA_military_zones/`)

**Source Format:** Two-column table with County, Census Tract, and inline designation dates

**Sample Raw Text:**
```
COUNTY          CENSUS TRACT†
Bryan           9203.01         Designation effective January 1, 2024
Camden          105.00          Designation effective January 1, 2024
Houston         204.00          Designation effective January 1, 2007
```

**Target Schema:**
```python
@dataclass
class MilitaryZoneRecord:
    year: int                    # Year of the PDF/designation list
    county: str                  # e.g., "Bryan", "Camden" (normalized)
    tract: str                   # e.g., "9203.01", "105.00" (just the number)
    effective_date: date         # Python date object for easy comparison
```

**Output Example (flat):**
```json
[
  {"year": 2024, "county": "Bryan", "tract": "9203.01", "effective_date": "2024-01-01"},
  {"year": 2024, "county": "Houston", "tract": "204.00", "effective_date": "2007-01-01"}
]
```

**Lookup-Friendly Alternative (grouped):**
```json
{
  "2024": {
    "Bryan": [
      {"tract": "9201.01", "effective_date": "2019-01-01"},
      {"tract": "9203.01", "effective_date": "2024-01-01"}
    ],
    "Camden": [
      {"tract": "102.02", "effective_date": "2024-01-01"},
      {"tract": "105.00", "effective_date": "2024-01-01"},
      {"tract": "106.03", "effective_date": "2023-01-01"}
    ]
  }
}
```

**Files to Process:**
- `2c_2020_mz_final_updated_7-30-2020.pdf` → year: 2020
- `2021_statewide_mzeligible_final.pdf` → year: 2021
- `Appendix D - 2022_MZ_FINAL_2-15-22.pdf` → year: 2022
- `appendix_e_-_2023_mz_final_1-19-23_updated_3-14-23_for_page_break_error.pdf` → year: 2023
- `appendix_e_final_2024_mzs.pdf` → year: 2024

---

### 3. State Opportunity Zones (`GA_opportunity_zones/`)

**Source Format:** Table with Named Area, Date Designated, and Designation Period

**Sample Raw Text:**
```
Designated Area *          Date Designated     Designation Period
Acworth                    March 5, 2021       2021 through 2030
Albany Downtown            December 23, 2023   2023 through 2032
Atlanta – Campbellton Road June 14, 2024       2024 though 2033
```

**Target Schema:**
```python
@dataclass
class OpportunityZoneRecord:
    area: str                    # e.g., "Acworth", "Albany Downtown" (cleaned)
    designated_date: date        # Python date: 2021-03-05
    start_year: int              # 2021
    end_year: int                # 2030
```

**Output Example:**
```json
[
  {"area": "Acworth", "designated_date": "2021-03-05", "start_year": 2021, "end_year": 2030},
  {"area": "Albany Downtown", "designated_date": "2023-12-23", "start_year": 2023, "end_year": 2032},
  {"area": "Atlanta - Campbellton Road", "designated_date": "2024-06-14", "start_year": 2024, "end_year": 2033}
]
```

**Note:** This data type is **structurally different** - it's about named areas with date ranges, NOT county/census tract mappings.

**Files to Process:**
- `State Opportunity Zones Designation Dates updated January 9 2026.pdf`

---

## Extraction Strategy by Type

### LDCT Extraction Strategy

**Challenges:**
- Multi-column layout (3+ columns per page)
- MSA headers span sections
- County names appear as headers before their census tracts
- "Census Tract XXX" repeated pattern

**Approach:**
1. **Text Extraction:** Use PyMuPDF's block-based extraction with coordinates
2. **MSA Detection:** Regex pattern: `^[A-Z][A-Z\s\-]+MSA$`
3. **County Detection:** Line that is NOT "Census Tract" and NOT an MSA → likely county name
4. **Census Tract Pattern:** Regex: `Census Tract (\d+(?:\.\d+)?)`
5. **State Machine:**
   - State: `current_msa`, `current_county`
   - When MSA detected → update `current_msa`, clear `current_county`
   - When County detected → update `current_county`
   - When Census Tract detected → emit record with current context

**Column Handling:**
- Sort text blocks by x-coordinate to process left-to-right
- Within each column, process top-to-bottom
- Use column boundaries to separate data streams

---

### Military Zone Extraction Strategy

**Challenges:**
- Two distinct sections with different subsection headers
- Designation dates are inline with census tracts
- County names repeat for each row

**Approach:**
1. **Text Extraction:** Full page text extraction (simpler layout)
2. **Row Pattern:** Regex: `^([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+(?:\.\d+)?)\s+Designation effective\s+(.+)$`
3. **Alternative:** Split by "Designation effective" and work backwards

**Simpler Pattern Match:**
```python
pattern = r'([A-Za-z]+(?:\s[A-Za-z]+)?)\s+(\d+\.\d{2})\s+Designation effective\s+(\w+\s+\d+,\s+\d{4})'
```

---

### Opportunity Zone Extraction Strategy

**Challenges:**
- Clean table format but with some multi-line entries (e.g., "Atlanta - Donald Lee Hollowell\nParkway - Grove Park")
- Date formats are consistent: "Month DD, YYYY"
- Period formats: "YYYY through YYYY" (with typo "though" in some entries)

**Approach:**
1. **Text Extraction:** Full page text extraction
2. **Table Detection:** Lines between header row and footer
3. **Row Pattern:** 
   - Area name: Everything before a date pattern
   - Date: `\w+ \d{1,2}, \d{4}`
   - Period: `\d{4} through \d{4}` (handle "though" typo)
4. **Multi-line Handling:** Merge lines that don't start with a recognizable pattern

---

## Implementation Plan

### Phase 1: Core Infrastructure

```
docex/
├── extractors/
│   ├── __init__.py
│   ├── base.py              # BaseExtractor class
│   ├── ldct.py              # Less Developed Census Tract extractor
│   ├── military_zone.py     # Military Zone extractor
│   └── opportunity_zone.py  # Opportunity Zone extractor
├── schema/
│   ├── __init__.py
│   ├── ldct.py              # LDCTRecord Pydantic model
│   ├── military_zone.py     # MilitaryZoneRecord Pydantic model
│   └── opportunity_zone.py  # OpportunityZoneRecord Pydantic model
├── utils/
│   ├── __init__.py
│   ├── pdf.py               # PyMuPDF helpers
│   └── text_processing.py   # Column detection, text normalization
├── output/
│   ├── __init__.py
│   └── writer.py            # JSON/CSV/Parquet output
├── main.py                  # CLI entry point
└── requirements.txt
```

### Phase 2: Extraction Order

1. **Start with LDCT** (most complex layout, highest value)
   - Implement column detection
   - Build state machine for MSA/County/Tract parsing
   - Validate against manual count

2. **Military Zones** (simpler structure)
   - Row-by-row parsing
   - Date extraction and validation

3. **Opportunity Zones** (table format, no census tracts)
   - Table parsing
   - Handle multi-line area names

### Phase 3: Output Generation

**Per Folder Output:**
```
data_folders/
├── GA_less_dev_cencus/
│   ├── [source PDFs]
│   └── extracted/
│       ├── ldct_2020.json
│       ├── ldct_2021.json
│       ├── ldct_2022.json
│       ├── ldct_2023.json
│       ├── ldct_2024.json
│       └── ldct_combined.json   # All years merged
├── GA_military_zones/
│   └── extracted/
│       ├── mz_2020.json
│       ├── mz_2021.json
│       ├── ...
│       └── mz_combined.json
└── GA_opportunity_zones/
    └── extracted/
        └── oz_current.json
```

**Combined Master Output:**
```
data_folders/
└── master/
    ├── ldct.json                # All LDCT years: {year: {county: [tracts]}}
    ├── military_zones.json      # All MZ years: {year: {county: [{tract, effective_date}]}}
    ├── opportunity_zones.json   # OZ list: [{area, designated_date, start_year, end_year}]
    └── tract_lookup.json        # Quick lookup by tract: {"13001020200": {ldct: [2022,2023], mz: []}}
```

**Tract Lookup Format (FIPS-based keys):**
```json
{
  "13177020200": {
    "county": "Lee",
    "tract": "202",
    "ldct_years": [2022, 2023, 2024],
    "mz_years": []
  },
  "13051920301": {
    "county": "Chatham",
    "tract": "9203.01",
    "ldct_years": [],
    "mz_years": [2020, 2021, 2022, 2023, 2024]
  }
}
```

---

## Validation Strategy

### Manual Spot Checks
For each PDF:
- Pick 3 random counties
- Count census tracts manually
- Compare to extracted count

### Cross-Year Validation
- Tracts should generally persist year-to-year
- Flag any tract that appears/disappears unexpectedly

### Data Integrity
- Tract format validation: `\d+(\.\d+)?` (just numbers, no prefix)
- No duplicate (county, tract, year) combinations per zone type
- All counties are valid Georgia county names (159 total)
- Dates parsed to ISO 8601 format: `YYYY-MM-DD`

---

## Dependencies

```
# Core
pymupdf>=1.23.0          # PDF text extraction with coordinates
pydantic>=2.0.0          # Data validation and serialization

# Output
pandas>=2.0.0            # Data manipulation
pyarrow>=14.0.0          # Parquet output (optional)

# Testing
pytest>=7.0.0            # Unit tests
```

---

## Quick Start Commands

```bash
# Extract single file
python -m docex.main extract data_folders/GA_less_dev_cencus/3d_final_2022_ldcts.pdf --type ldct

# Extract entire folder
python -m docex.main extract-folder data_folders/GA_less_dev_cencus/ --type ldct

# Extract all folders
python -m docex.main extract-all data_folders/ --output data_folders/master/
```

---

## Open Questions

1. **Do you want a unified view?** A single lookup where you can query "Is census tract 202 in Lee County eligible for any incentives in 2024?" across all zone types?

2. **Historical tracking?** Should we track when tracts were added/removed between years?

3. **Additional metadata?** The Military Zone PDFs reference specific statutes (O.C.G.A. § 48-7-40.1(c)(2)). Should we preserve this?

4. **Geocoding?** Would it be helpful to add lat/long coordinates for census tracts (requires external data)?

---

## Next Steps

1. [ ] Scaffold basic project structure
2. [ ] Implement LDCT extractor for 2022 PDF (test case)
3. [ ] Validate extraction accuracy
4. [ ] Extend to other years and zone types
5. [ ] Build output consolidation

