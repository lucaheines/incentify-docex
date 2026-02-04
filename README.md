# Georgia Tax Incentive Zone Extractor (docex)

A PDF extraction tool for Georgia tax incentive zone data. Extracts census tract designations from official Georgia DCA PDFs into clean, structured JSON.

## Zone Types Supported

| Zone Type | Description | Output Format |
|-----------|-------------|---------------|
| **LDCT** | Less Developed Census Tracts | `{year: {county: [tracts]}}` |
| **Military Zones** | Military Zone Census Tracts | `{year: {county: [{tract, effective_date}]}}` |
| **Opportunity Zones** | State Opportunity Zones | `[{area, designated_date, start_year, end_year}]` |

## Quick Start

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# For OCR support (scanned PDFs), install Tesseract:
# macOS: brew install tesseract
# Ubuntu: sudo apt install tesseract-ocr

# Extract all zone types
python -m docex.main extract-all data_folders/

# Or extract specific types
python -m docex.main extract-ldct data_folders/GA_less_dev_cencus/
python -m docex.main extract-mz data_folders/GA_military_zones/
python -m docex.main extract-oz data_folders/GA_opportunity_zones/
```

## Output Examples

### LDCT (Less Developed Census Tracts)
```json
{
  "Lee": ["202", "203"],
  "Fulton": ["7", "10.02", "19", "21", "23", "24", "25", ...],
  "Worth": ["9501", "9502", "9505"]
}
```

### Military Zones
```json
{
  "Bryan": [
    {"tract": "9203.01", "effective_date": "2024-01-01"},
    {"tract": "9201.01", "effective_date": "2019-01-01"}
  ]
}
```

### Opportunity Zones
```json
[
  {"area": "Acworth", "designated_date": "2021-03-05", "start_year": 2021, "end_year": 2030},
  {"area": "Atlanta - Downtown", "designated_date": "2022-01-19", "start_year": 2022, "end_year": 2031}
]
```

## Validation

```bash
# Full validation report
python -m docex.validate full ldct data_folders/GA_less_dev_cencus/extracted/

# Compare two years
python -m docex.validate compare 2022 2023 data_folders/GA_less_dev_cencus/extracted/

# Spot-check a specific county
python -m docex.validate spot-check Fulton data_folders/GA_less_dev_cencus/extracted/
```

## Build Census Tract GEOIDs

Generate full 11-digit GEOIDs (State + County FIPS + Tract) for use with GeoJSON/mapping:

```bash
# Get 2024 LDCT GEOIDs as comma-separated list
python -m docex.build_geoids ldct 2024 data_folders/GA_less_dev_cencus/extracted/

# All years combined
python -m docex.build_geoids ldct all data_folders/GA_less_dev_cencus/extracted/

# Military Zones
python -m docex.build_geoids mz 2024 data_folders/GA_military_zones/extracted/

# Save to output folder
python -m docex.build_geoids ldct 2024 data_folders/GA_less_dev_cencus/extracted/ -o output/ldct_2024_geoids.csv
```

GEOID format: `13` (GA) + `177` (Lee County) + `020200` (Tract 202) = `13177020200`

## Data Sources

PDFs are sourced from the Georgia Department of Community Affairs:
- [Less Developed Census Tracts](https://www.dca.ga.gov/)
- [Military Zones](https://www.dca.ga.gov/)
- [State Opportunity Zones](https://dca.georgia.gov/financing-tools/incentives/state-opportunity-zones)

## Project Structure

```
incentify-docex/
├── docex/                       # Extraction code
│   ├── extractors/
│   │   ├── ldct.py              # LDCT extractor (handles OCR)
│   │   ├── military_zone.py     # Military Zone extractor
│   │   └── opportunity_zone.py  # Opportunity Zone extractor
│   ├── schema/                  # Pydantic models
│   ├── utils/
│   │   └── ocr.py               # OCR for scanned PDFs
│   ├── main.py                  # Extraction CLI
│   ├── validate.py              # Validation tools
│   └── build_geoids.py          # GEOID builder
│
├── data_folders/
│   ├── GA_less_dev_cencus/
│   │   ├── *.pdf                # Source PDFs
│   │   └── extracted/           # JSON outputs
│   ├── GA_military_zones/
│   │   ├── *.pdf
│   │   └── extracted/
│   ├── GA_opportunity_zones/
│   │   ├── *.pdf
│   │   └── extracted/
│   └── _reference/
│       └── us-counties.geojson  # County FIPS lookup
│
├── output/                      # Generated files (GEOIDs, etc.)
├── requirements.txt
└── README.md
```

## Extracted Data Summary

| Zone Type | Years | Total Records |
|-----------|-------|---------------|
| LDCT | 2020-2024 | ~2,350 tract designations |
| Military Zones | 2020, 2022-2024 | ~360 tract designations |
| Opportunity Zones | Current | 31 designated areas |

## Notes

- The 2020 LDCT PDF is scanned (image-based) and uses OCR extraction
- The 2021 Military Zone file is a map visualization (not extractable)
- All tract numbers are clean strings (e.g., `"202"` not `"Census Tract 202"`)
- Dates are ISO 8601 format (`"2024-01-01"`)

## License

MIT

