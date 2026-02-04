# docex — PDF Extraction Engine

## Project Overview

A high-accuracy, open-source PDF extraction pipeline designed for reliability and debuggability. Extracts structured data from PDFs (digital or scanned) with full provenance tracking.

**Core Philosophy:** Accuracy comes from layered defense—detect what you have → extract with the right tool → validate strictly → never guess silently. Every extracted value carries provenance so you can debug failures.

---

## Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Rendering & Repair | PyMuPDF (fitz), pikepdf | Fast page rendering, text extraction, handle corrupted/encrypted PDFs |
| OCR | PaddleOCR, OpenCV | OCR for scanned docs, preprocessing (deskew/denoise) |
| Layout Detection | LayoutParser + Detectron2 | Identify tables, headers, content regions |
| Table Extraction | Camelot, Tabula | Vector-based tables (Camelot primary, Tabula fallback) |
| Validation | Pydantic | Strict typing, ranges, required fields |
| Output | JSON, Parquet | Provenance-rich JSON, analytics-friendly Parquet |

---

## Pipeline Stages

```
PREFLIGHT → PARSE → LAYOUT → EXTRACT → RESOLVE → VALIDATE → OUTPUT
```

### 1. Preflight
- Classify PDF: digital / scanned / hybrid
- Extract metadata: hash, page count, rotation
- Repair if needed (pikepdf)

### 2. Parse
- Digital text → extract with coordinates via PyMuPDF
- Scanned regions → OCR with PaddleOCR
- Unify into normalized token list:
  ```python
  Token = {
      "text": str,
      "page": int,
      "bbox": [x0, y0, x1, y1],
      "source": "pdf" | "ocr"
  }
  ```

### 3. Layout
- Segment page into blocks using LayoutParser
- Block types: `table | header | paragraph | figure`
- Each block contains: `{type, bbox, page, tokens[]}`

### 4. Extract
- **Rules-first:** anchors + proximity + regex patterns
- **Model fallback:** LayoutLMv3 on ambiguous regions (only when rules fail)
- Generate multiple candidates per field with confidence scores

### 5. Resolve
- Pick best candidate per field based on:
  - Proximity to anchor
  - Pattern match quality
  - Column alignment
  - Cross-field consistency (dates match, totals add up)

### 6. Validate
- Type casting (string → float, date parsing)
- Unit normalization (% vs decimal)
- Range checks
- Required field enforcement
- **Reject bad data rather than guess**

### 7. Output
- JSON with full provenance
- Parquet for analytics
- Debug bundle: page images, OCR text, layout blocks

---

## Field Output Contract

Every extracted field follows this structure:

```python
@dataclass
class ExtractedField:
    field: str                    # canonical field name
    value: Any                    # extracted value (typed)
    confidence: float             # 0.0 - 1.0
    evidence: Evidence            # provenance
    status: Literal["ok", "missing", "ambiguous", "failed_validation"]

@dataclass
class Evidence:
    page: int
    bbox: list[float]             # [x0, y0, x1, y1]
    text_snippet: str             # source text that produced the value
```

Example output:
```json
{
    "field": "unemployment_rate",
    "value": 7.2,
    "confidence": 0.93,
    "evidence": {
        "page": 3,
        "bbox": [120.5, 340.2, 280.1, 355.8],
        "text_snippet": "Unemployment rate: 7.2%"
    },
    "status": "ok"
}
```

---

## Extraction Strategies

Configurable per field:

| Strategy | Description |
|----------|-------------|
| `table_column` | Find header text, extract values from that column |
| `label_right` | Find anchor label, take value immediately to the right |
| `label_below` | Find anchor label, take value below |
| `section_scoped` | Search only within a named section |
| `regex_pattern` | Match specific patterns in nearby text |

### Synonym Dictionary

Each field has anchor variants:
```yaml
unemployment_rate:
  - "Unemployment rate"
  - "Jobless rate"
  - "Unemp."
  - "Unemployment (%)"

gdp_growth:
  - "GDP growth"
  - "Real GDP"
  - "Economic growth"
```

---

## Project Structure

```
docex/
├── core/
│   ├── __init__.py
│   ├── preflight.py      # PDF classification, metadata extraction
│   ├── parser.py         # Text/OCR extraction, token unification
│   ├── layout.py         # Block segmentation via LayoutParser
│   └── resolver.py       # Candidate selection, cross-field consistency
│
├── extractors/
│   ├── __init__.py
│   ├── base.py           # Extractor interface / base class
│   ├── table.py          # Table-based extraction (Camelot/Tabula)
│   ├── label.py          # Label-proximity extraction
│   └── model.py          # ML fallback (LayoutLMv3)
│
├── schema/
│   ├── __init__.py
│   ├── fields.py         # Pydantic models for extracted fields
│   └── validators.py     # Custom validation logic
│
├── config/
│   ├── synonyms.yaml     # Field → anchor variants mapping
│   └── profiles/         # Per-document-type configs
│
├── eval/
│   ├── gold/             # Ground truth labeled data
│   ├── harness.py        # Accuracy measurement & regression tests
│   └── metrics.py        # Exact match, tolerance match, etc.
│
├── output/
│   ├── __init__.py
│   └── writer.py         # JSON/Parquet output with provenance
│
├── utils/
│   ├── __init__.py
│   ├── ocr.py            # PaddleOCR wrapper
│   ├── preprocess.py     # OpenCV deskew/denoise
│   └── pdf.py            # PyMuPDF/pikepdf helpers
│
├── main.py               # CLI entry point
├── pipeline.py           # Orchestrates full extraction flow
└── requirements.txt
```

---

## Accuracy Infrastructure

Build from day 1:

### Gold Dataset
- 50–200 manually labeled documents
- Ground truth values for all target fields
- Stored in `eval/gold/`

### Eval Harness
Metrics to track:
- **Exact match rate** — value matches ground truth exactly
- **Tolerance match** — floats within acceptable range (e.g., ±0.1)
- **Missing rate** — fields that should exist but weren't found
- **False positive rate** — fields extracted that shouldn't be

### Regression Tests
- Any code change must not decrease accuracy on gold set
- CI/CD integration: block merges that reduce accuracy

---

## Key Design Decisions

1. **Rules-first, ML-second** — ML models are fallback, not primary. Rules are debuggable.

2. **Provenance everywhere** — Every value traces back to page, bbox, source text.

3. **Fail loudly** — Status field shows `missing` or `failed_validation` rather than guessing.

4. **Config-driven fields** — New document types = new config, not new code.

5. **Unified token representation** — PDF text and OCR text both become the same Token structure.

---

## Dependencies

```
# Core PDF handling
pymupdf>=1.23.0
pikepdf>=8.0.0

# OCR
paddleocr>=2.7.0
paddlepaddle>=2.5.0
opencv-python>=4.8.0

# Layout detection
layoutparser>=0.3.4
detectron2>=0.6

# Table extraction
camelot-py>=0.11.0
tabula-py>=2.8.0

# Schema & validation
pydantic>=2.0.0

# Output
pyarrow>=14.0.0
pandas>=2.0.0

# ML fallback (optional)
transformers>=4.35.0
torch>=2.0.0
```

---

## Open Questions (answer before implementation)

1. **PDF type:** Mostly digital text or scans?
2. **Data location:** Mostly in tables or key-value sections?
3. **Target fields:** What's the rough schema? (even 10–20 fields helps)

---

## Usage (target API)

```python
from docex import Pipeline
from docex.schema import MyDocumentSchema

# Initialize pipeline
pipeline = Pipeline(
    schema=MyDocumentSchema,
    synonyms="config/synonyms.yaml",
    use_ocr=True
)

# Extract from PDF
result = pipeline.extract("document.pdf")

# Access fields with provenance
for field in result.fields:
    print(f"{field.field}: {field.value} (confidence: {field.confidence})")
    print(f"  Source: page {field.evidence.page}, '{field.evidence.text_snippet}'")

# Export
result.to_json("output.json")
result.to_parquet("output.parquet")
```

---

## Next Steps

1. Scaffold project structure
2. Implement `core/preflight.py` — PDF classification
3. Implement `core/parser.py` — text extraction + OCR unification
4. Implement `core/layout.py` — block segmentation
5. Build first extractor (likely `label.py`)
6. Add Pydantic schema
7. Wire up full pipeline
8. Create eval harness with sample gold data
