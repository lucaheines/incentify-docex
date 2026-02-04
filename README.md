# Georgia Tax Incentive Zone Extractor

Extract census tract designations from Georgia DCA PDFs into structured JSON and build GEOIDs for mapping.

## What This Does

Georgia offers tax incentives for businesses in designated zones. This tool extracts the census tract data from official PDFs published by the Georgia Department of Community Affairs, producing:

1. **Structured JSON** — County → tract mappings for each year
2. **11-digit GEOIDs** — Census tract identifiers compatible with GeoJSON/mapping tools

## Supported Zone Types

| Zone Type | Years Available | Description |
|-----------|-----------------|-------------|
| **LDCT** (Less Developed Census Tracts) | 2020–2024 | Job tax credits for economically distressed areas |
| **Military Zones** | 2020, 2022–2024 | Tax incentives near military installations |
| **Opportunity Zones** | Current (2026) | State-designated opportunity zones with designation dates |

## Quick Start

```bash
# Clone and setup
git clone https://github.com/YOUR_ORG/incentify-docex.git
cd incentify-docex
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# For OCR support (required for 2020 LDCT - scanned PDF)
# macOS: brew install tesseract
# Ubuntu: sudo apt install tesseract-ocr
```

## Usage

### Extract Data from PDFs

```bash
# Extract all zone types
python -m docex.main

# Or extract specific types
python -m docex.main --ldct-only
python -m docex.main --mz-only
python -m docex.main --oz-only
```

### Build GEOIDs

```bash
# LDCT GEOIDs for a specific year (outputs to terminal)
python -m docex.build_geoids ldct 2024 data_folders/GA_less_dev_cencus/extracted/

# All LDCT years combined
python -m docex.build_geoids ldct all data_folders/GA_less_dev_cencus/extracted/

# Military Zones
python -m docex.build_geoids mz 2024 data_folders/GA_military_zones/extracted/

# Save to file
python -m docex.build_geoids ldct 2024 data_folders/GA_less_dev_cencus/extracted/ -o output/ldct/geoids_2024.csv
```

**GEOID format:** `13` (Georgia) + `177` (Lee County FIPS) + `020200` (Tract 202) = `13177020200`

### Validate Extracted Data

```bash
# Full validation report
python -m docex.validate full ldct data_folders/GA_less_dev_cencus/extracted/

# Compare changes between years
python -m docex.validate compare 2023 2024 data_folders/GA_less_dev_cencus/extracted/

# Spot-check a specific county
python -m docex.validate spot-check Fulton data_folders/GA_less_dev_cencus/extracted/
```

## Output

### Extracted JSON (in `data_folders/*/extracted/`)

**LDCT** — `ldct_2024.json`
```json
{
  "Lee": ["202", "203"],
  "Fulton": ["7", "10.02", "19", "21", "23", "24", "25"],
  "Worth": ["9501", "9502", "9505"]
}
```

**Military Zones** — `mz_2024.json`
```json
{
  "Bryan": [
    {"tract": "9203.01", "effective_date": "2024-01-01"},
    {"tract": "9201.01", "effective_date": "2019-01-01"}
  ]
}
```

**Opportunity Zones** — `opportunity_zones.json`
```json
[
  {"area": "Acworth", "designated_date": "2021-03-05", "start_year": 2021, "end_year": 2030},
  {"area": "Atlanta - Downtown", "designated_date": "2022-01-19", "start_year": 2022, "end_year": 2031}
]
```

### Generated GEOIDs (in `output/`)

```
output/
├── ldct/
│   ├── geoids_2020.csv     342 unique tracts
│   ├── geoids_2021.csv     488 unique tracts
│   ├── geoids_2022.csv     471 unique tracts
│   ├── geoids_2023.csv     557 unique tracts
│   ├── geoids_2024.csv     492 unique tracts
│   └── geoids_all.csv      1,004 unique (all years combined)
│
└── military_zones/
    ├── geoids_2020.csv     69 unique tracts
    ├── geoids_2022.csv     83 unique tracts
    ├── geoids_2023.csv     91 unique tracts
    ├── geoids_2024.csv     93 unique tracts
    └── geoids_all.csv      141 unique (all years combined)
```

Each CSV is a single line of comma-separated 11-digit GEOIDs, ready for filtering GeoJSON features.

## Project Structure

```
incentify-docex/
├── docex/                          # Python package
│   ├── extractors/                 # PDF extraction logic
│   │   ├── ldct.py                 # LDCT extractor (w/ OCR support)
│   │   ├── military_zone.py        # Military Zone extractor
│   │   └── opportunity_zone.py     # Opportunity Zone extractor
│   ├── schema/                     # Pydantic data models
│   ├── utils/
│   │   └── ocr.py                  # Tesseract OCR utilities
│   ├── main.py                     # Extraction CLI
│   ├── validate.py                 # Data validation tools
│   └── build_geoids.py             # GEOID generation
│
├── data_folders/                   # Input PDFs & extracted data
│   ├── GA_less_dev_cencus/
│   │   ├── *.pdf                   # Source PDFs (2020–2024)
│   │   └── extracted/              # Output JSON
│   ├── GA_military_zones/
│   │   ├── *.pdf                   # Source PDFs
│   │   └── extracted/              # Output JSON
│   ├── GA_opportunity_zones/
│   │   ├── *.pdf                   # Source PDF
│   │   └── extracted/              # Output JSON
│   └── _reference/
│       └── us-counties.geojson     # County FIPS codes for GEOID building
│
├── output/                         # Generated GEOIDs (gitignored)
│   ├── ldct/
│   └── military_zones/
│
├── EXTRACTION_PLAN.md              # Detailed extraction methodology
├── requirements.txt
└── README.md
```

## Data Sources

All PDFs are official publications from the Georgia Department of Community Affairs:

- **LDCT**: [Job Tax Credit Less Developed Census Tracts](https://www.dca.ga.gov/community-economic-development/incentive-programs/job-tax-credit)
- **Military Zones**: [Military Zone Program](https://www.dca.ga.gov/community-economic-development/incentive-programs/military-zone-tax-credit)
- **Opportunity Zones**: [State Opportunity Zones](https://dca.georgia.gov/financing-tools/incentives/state-opportunity-zones)

## Technical Notes

- **OCR Support**: The 2020 LDCT PDF is a scanned document (image-based). Tesseract OCR is used for extraction.
- **2021 Military Zones**: This file is a map visualization only — no tabular data to extract.
- **Clean Values**: Tract numbers are normalized (e.g., `"202"` not `"Census Tract 202"`)
- **ISO 8601 Dates**: All dates use `YYYY-MM-DD` format

## Requirements

- Python 3.10+
- Tesseract OCR (for scanned PDFs)

```
pymupdf>=1.23.0
pydantic>=2.0
pytesseract>=0.3.10
Pillow>=10.0
```

## License

MIT
