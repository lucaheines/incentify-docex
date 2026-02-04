"""
Build full Census Tract GEOIDs from extracted zone data.

GEOID format: STATE_FIPS (2) + COUNTY_FIPS (3) + TRACT (6) = 11 digits
Example: 13 + 089 + 960100 = 13089960100

Usage:
    python -m docex.build_geoids ldct 2024 data_folders/GA_less_dev_cencus/extracted/
    python -m docex.build_geoids ldct all data_folders/GA_less_dev_cencus/extracted/
    python -m docex.build_geoids mz 2024 data_folders/GA_military_zones/extracted/
"""

import argparse
import json
import re
from pathlib import Path


# Georgia State FIPS
STATE_FIPS = "13"


def load_ga_county_fips(geojson_path: Path) -> dict[str, str]:
    """
    Load Georgia counties from us-counties.geojson and return name -> FIPS mapping.
    
    Returns:
        Dict mapping county name (lowercase) to 3-digit FIPS code
    """
    with open(geojson_path) as f:
        data = json.load(f)
    
    county_fips = {}
    
    for feature in data["features"]:
        props = feature.get("properties", {})
        
        # Only Georgia (STATEFP = 13)
        if props.get("STATEFP") != "13":
            continue
        
        name = props.get("NAME", "").lower()
        fips = props.get("COUNTYFP", "")
        
        if name and fips:
            county_fips[name] = fips
    
    return county_fips


def normalize_county_name(name: str) -> str:
    """Normalize county name for matching."""
    name = name.lower().strip()
    # Handle common variations
    name = name.replace("dekalb", "dekalb")  # Already lowercase
    name = name.replace("mcintosh", "mcintosh")
    name = name.replace("mcduffie", "mcduffie")
    return name


def tract_to_6digit(tract: str) -> str:
    """
    Convert tract number to 6-digit format for GEOID.
    
    Examples:
        "202" -> "020200"
        "9601" -> "960100"
        "9601.02" -> "960102"
        "103.01" -> "010301"
    """
    # Remove any whitespace
    tract = tract.strip()
    
    # Handle decimal tracts (e.g., "9601.02")
    if "." in tract:
        whole, decimal = tract.split(".")
        # Decimal part is always 2 digits
        decimal = decimal.zfill(2)[:2]
    else:
        whole = tract
        decimal = "00"
    
    # Whole part should be 4 digits
    whole = whole.zfill(4)
    
    # Combine: 4 digits + 2 digits = 6 digits
    return whole + decimal


def build_geoid(county_fips: str, tract: str) -> str:
    """Build full 11-digit GEOID."""
    tract_6 = tract_to_6digit(tract)
    return f"{STATE_FIPS}{county_fips}{tract_6}"


def load_ldct_data(extracted_dir: Path, year: str = "all") -> dict:
    """Load LDCT data for specified year(s)."""
    if year == "all":
        combined_file = extracted_dir / "ldct_combined.json"
        with open(combined_file) as f:
            return json.load(f)
    else:
        year_file = extracted_dir / f"ldct_{year}.json"
        with open(year_file) as f:
            data = json.load(f)
            return {year: data}


def load_mz_data(extracted_dir: Path, year: str = "all") -> dict:
    """Load Military Zone data for specified year(s)."""
    if year == "all":
        combined_file = extracted_dir / "mz_combined.json"
        with open(combined_file) as f:
            return json.load(f)
    else:
        year_file = extracted_dir / f"mz_{year}.json"
        with open(year_file) as f:
            data = json.load(f)
            return {year: data}


def build_geoids_from_ldct(
    ldct_data: dict,
    county_fips_map: dict,
    year_filter: str = "all"
) -> tuple[list[str], list[str]]:
    """
    Build GEOIDs from LDCT data.
    
    Returns:
        Tuple of (geoid_list, errors)
    """
    geoids = set()
    errors = []
    
    for year, year_data in ldct_data.items():
        if year_filter != "all" and year != year_filter:
            continue
        
        for county, tracts in year_data.items():
            county_norm = normalize_county_name(county)
            
            if county_norm not in county_fips_map:
                errors.append(f"County not found: {county}")
                continue
            
            county_fips = county_fips_map[county_norm]
            
            for tract in tracts:
                try:
                    geoid = build_geoid(county_fips, tract)
                    geoids.add(geoid)
                except Exception as e:
                    errors.append(f"Error building GEOID for {county}/{tract}: {e}")
    
    return sorted(geoids), errors


def build_geoids_from_mz(
    mz_data: dict,
    county_fips_map: dict,
    year_filter: str = "all"
) -> tuple[list[str], list[str]]:
    """
    Build GEOIDs from Military Zone data.
    
    Returns:
        Tuple of (geoid_list, errors)
    """
    geoids = set()
    errors = []
    
    for year, year_data in mz_data.items():
        if year_filter != "all" and year != year_filter:
            continue
        
        for county, tract_records in year_data.items():
            county_norm = normalize_county_name(county)
            
            if county_norm not in county_fips_map:
                errors.append(f"County not found: {county}")
                continue
            
            county_fips = county_fips_map[county_norm]
            
            for record in tract_records:
                tract = record["tract"] if isinstance(record, dict) else record
                try:
                    geoid = build_geoid(county_fips, tract)
                    geoids.add(geoid)
                except Exception as e:
                    errors.append(f"Error building GEOID for {county}/{tract}: {e}")
    
    return sorted(geoids), errors


def main():
    parser = argparse.ArgumentParser(
        description="Build Census Tract GEOIDs from extracted zone data"
    )
    parser.add_argument(
        "zone_type",
        choices=["ldct", "mz"],
        help="Zone type to process"
    )
    parser.add_argument(
        "year",
        help="Year to process (e.g., '2024') or 'all' for all years"
    )
    parser.add_argument(
        "extracted_dir",
        type=Path,
        help="Directory containing extracted JSON files"
    )
    parser.add_argument(
        "--geojson",
        type=Path,
        default=Path("data_folders/_reference/us-counties.geojson"),
        help="Path to us-counties.geojson"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file (default: print to stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "list", "json"],
        default="csv",
        help="Output format: csv (comma-separated), list (one per line), json"
    )
    
    args = parser.parse_args()
    
    # Load county FIPS mapping
    print(f"Loading Georgia counties from {args.geojson}...", file=__import__('sys').stderr)
    county_fips_map = load_ga_county_fips(args.geojson)
    print(f"  Found {len(county_fips_map)} Georgia counties", file=__import__('sys').stderr)
    
    # Load zone data and build GEOIDs
    if args.zone_type == "ldct":
        data = load_ldct_data(args.extracted_dir, args.year)
        geoids, errors = build_geoids_from_ldct(data, county_fips_map, args.year)
    else:
        data = load_mz_data(args.extracted_dir, args.year)
        geoids, errors = build_geoids_from_mz(data, county_fips_map, args.year)
    
    # Report errors
    if errors:
        print(f"\nWarnings ({len(errors)}):", file=__import__('sys').stderr)
        for err in set(errors):
            print(f"  ⚠ {err}", file=__import__('sys').stderr)
    
    print(f"\nGenerated {len(geoids)} unique GEOIDs", file=__import__('sys').stderr)
    
    # Format output
    if args.format == "csv":
        output = ",".join(geoids)
    elif args.format == "list":
        output = "\n".join(geoids)
    else:  # json
        output = json.dumps(geoids, indent=2)
    
    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=__import__('sys').stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()

