"""
Validation utilities for cross-checking extracted data.

Usage:
    python -m docex.validate ldct data_folders/GA_less_dev_cencus/extracted/
    python -m docex.validate compare 2022 2023 data_folders/GA_less_dev_cencus/extracted/
    python -m docex.validate spot-check Lee data_folders/GA_less_dev_cencus/extracted/
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict


def load_ldct_combined(extracted_dir: Path) -> dict:
    """Load the combined LDCT JSON."""
    combined_file = extracted_dir / "ldct_combined.json"
    if not combined_file.exists():
        raise FileNotFoundError(f"Combined file not found: {combined_file}")
    
    with open(combined_file) as f:
        return json.load(f)


def load_mz_combined(extracted_dir: Path) -> dict:
    """Load the combined MZ JSON."""
    combined_file = extracted_dir / "mz_combined.json"
    if not combined_file.exists():
        raise FileNotFoundError(f"Combined file not found: {combined_file}")
    
    with open(combined_file) as f:
        return json.load(f)


def summary_stats(data: dict, zone_type: str = "ldct"):
    """Print summary statistics for extracted data."""
    print(f"\n{'='*60}")
    print(f"Summary Statistics - {zone_type.upper()}")
    print(f"{'='*60}\n")
    
    for year in sorted(data.keys()):
        year_data = data[year]
        counties = len(year_data)
        
        if zone_type == "ldct":
            total_tracts = sum(len(tracts) for tracts in year_data.values())
        else:  # mz
            total_tracts = sum(len(tracts) for tracts in year_data.values())
        
        print(f"{year}: {counties:3} counties, {total_tracts:4} tracts")
    
    print()


def year_over_year_comparison(data: dict, year1: str, year2: str, zone_type: str = "ldct"):
    """Compare two years to find added/removed counties and tracts."""
    print(f"\n{'='*60}")
    print(f"Year-over-Year Comparison: {year1} → {year2}")
    print(f"{'='*60}\n")
    
    if year1 not in data:
        print(f"ERROR: Year {year1} not found")
        return
    if year2 not in data:
        print(f"ERROR: Year {year2} not found")
        return
    
    data1 = data[year1]
    data2 = data[year2]
    
    counties1 = set(data1.keys())
    counties2 = set(data2.keys())
    
    added_counties = counties2 - counties1
    removed_counties = counties1 - counties2
    common_counties = counties1 & counties2
    
    print(f"Counties in {year1}: {len(counties1)}")
    print(f"Counties in {year2}: {len(counties2)}")
    print()
    
    if added_counties:
        print(f"Counties ADDED in {year2}: ({len(added_counties)})")
        for c in sorted(added_counties):
            tracts = data2[c]
            print(f"  + {c}: {tracts[:5]}{'...' if len(tracts) > 5 else ''}")
        print()
    
    if removed_counties:
        print(f"Counties REMOVED in {year2}: ({len(removed_counties)})")
        for c in sorted(removed_counties):
            tracts = data1[c]
            print(f"  - {c}: {tracts[:5]}{'...' if len(tracts) > 5 else ''}")
        print()
    
    # Check tract changes in common counties
    tract_changes = []
    for county in common_counties:
        if zone_type == "ldct":
            tracts1 = set(data1[county])
            tracts2 = set(data2[county])
        else:
            tracts1 = set(t["tract"] for t in data1[county])
            tracts2 = set(t["tract"] for t in data2[county])
        
        added = tracts2 - tracts1
        removed = tracts1 - tracts2
        
        if added or removed:
            tract_changes.append((county, added, removed))
    
    if tract_changes:
        print(f"Tract changes in existing counties: ({len(tract_changes)} counties)")
        for county, added, removed in sorted(tract_changes)[:15]:
            if added:
                print(f"  {county}: +{len(added)} tracts ({list(added)[:3]}{'...' if len(added) > 3 else ''})")
            if removed:
                print(f"  {county}: -{len(removed)} tracts ({list(removed)[:3]}{'...' if len(removed) > 3 else ''})")
        
        if len(tract_changes) > 15:
            print(f"  ... and {len(tract_changes) - 15} more counties with changes")
    else:
        print("No tract changes in common counties.")
    
    print()


def spot_check_county(data: dict, county_name: str):
    """Show a specific county's data across all years for manual verification."""
    print(f"\n{'='*60}")
    print(f"Spot Check: {county_name}")
    print(f"{'='*60}\n")
    
    found = False
    for year in sorted(data.keys()):
        # Case-insensitive search
        for county in data[year]:
            if county.lower() == county_name.lower():
                tracts = data[year][county]
                print(f"{year}: {tracts}")
                found = True
                break
    
    if not found:
        print(f"County '{county_name}' not found in any year.")
        # Suggest similar names
        all_counties = set()
        for year_data in data.values():
            all_counties.update(year_data.keys())
        
        similar = [c for c in all_counties if county_name.lower() in c.lower()]
        if similar:
            print(f"\nDid you mean: {similar}")
    
    print()


def find_anomalies(data: dict):
    """Find potential data quality issues."""
    print(f"\n{'='*60}")
    print("Anomaly Detection")
    print(f"{'='*60}\n")
    
    issues = []
    
    # Check for duplicate tracts within same county/year
    for year in data:
        for county, tracts in data[year].items():
            if isinstance(tracts, list):
                if len(tracts) != len(set(tracts)):
                    dupes = [t for t in tracts if tracts.count(t) > 1]
                    issues.append(f"{year}/{county}: Duplicate tracts: {set(dupes)}")
    
    # Check for unusual tract counts (very high or low)
    all_counts = []
    for year in data:
        for county, tracts in data[year].items():
            count = len(tracts) if isinstance(tracts, list) else len(tracts)
            all_counts.append((year, county, count))
    
    if all_counts:
        avg_count = sum(c[2] for c in all_counts) / len(all_counts)
        high_outliers = [(y, c, n) for y, c, n in all_counts if n > avg_count * 3]
        
        if high_outliers:
            issues.append(f"High tract counts (>3x average of {avg_count:.1f}):")
            for y, c, n in sorted(high_outliers, key=lambda x: -x[2])[:5]:
                issues.append(f"  {y}/{c}: {n} tracts")
    
    # Check for tract format issues
    for year in data:
        for county, tracts in data[year].items():
            if isinstance(tracts, list):
                for tract in tracts:
                    if not tract.replace(".", "").isdigit():
                        issues.append(f"{year}/{county}: Invalid tract format: {tract}")
    
    if issues:
        print("Potential issues found:")
        for issue in issues[:20]:
            print(f"  ⚠ {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
    else:
        print("✓ No anomalies detected")
    
    print()


def consistency_check(data: dict):
    """Check data consistency across years."""
    print(f"\n{'='*60}")
    print("Consistency Analysis")
    print(f"{'='*60}\n")
    
    # Track tract appearances
    tract_years = defaultdict(lambda: defaultdict(set))
    
    for year in data:
        for county, tracts in data[year].items():
            if isinstance(tracts, list):
                for tract in tracts:
                    tract_years[county][tract].add(year)
    
    # Find tracts that appear/disappear erratically
    years = sorted(data.keys())
    erratic = []
    
    for county, tract_data in tract_years.items():
        for tract, appeared_years in tract_data.items():
            appeared = sorted(appeared_years)
            # Check if there are gaps (appeared, disappeared, reappeared)
            if len(appeared) >= 2:
                year_indices = [years.index(y) for y in appeared]
                for i in range(len(year_indices) - 1):
                    if year_indices[i+1] - year_indices[i] > 1:
                        # There's a gap
                        erratic.append((county, tract, appeared))
                        break
    
    if erratic:
        print(f"Tracts with gaps (appeared, disappeared, reappeared): {len(erratic)}")
        for county, tract, appeared in erratic[:10]:
            print(f"  {county} / {tract}: appeared in {appeared}")
        if len(erratic) > 10:
            print(f"  ... and {len(erratic) - 10} more")
    else:
        print("✓ No erratic appearances detected")
    
    print()


def main():
    parser = argparse.ArgumentParser(description="Validate extracted zone data")
    subparsers = parser.add_subparsers(dest="command")
    
    # Summary command
    p_summary = subparsers.add_parser("summary", help="Show summary statistics")
    p_summary.add_argument("zone_type", choices=["ldct", "mz"], help="Zone type")
    p_summary.add_argument("extracted_dir", type=Path, help="Directory with extracted JSON files")
    
    # Compare command
    p_compare = subparsers.add_parser("compare", help="Compare two years")
    p_compare.add_argument("year1", help="First year")
    p_compare.add_argument("year2", help="Second year")
    p_compare.add_argument("extracted_dir", type=Path)
    p_compare.add_argument("--type", choices=["ldct", "mz"], default="ldct")
    
    # Spot-check command
    p_spot = subparsers.add_parser("spot-check", help="Check specific county")
    p_spot.add_argument("county", help="County name")
    p_spot.add_argument("extracted_dir", type=Path)
    p_spot.add_argument("--type", choices=["ldct", "mz"], default="ldct")
    
    # Full validation
    p_full = subparsers.add_parser("full", help="Run all validation checks")
    p_full.add_argument("zone_type", choices=["ldct", "mz"])
    p_full.add_argument("extracted_dir", type=Path)
    
    args = parser.parse_args()
    
    if args.command == "summary":
        if args.zone_type == "ldct":
            data = load_ldct_combined(args.extracted_dir)
        else:
            data = load_mz_combined(args.extracted_dir)
        summary_stats(data, args.zone_type)
    
    elif args.command == "compare":
        if args.type == "ldct":
            data = load_ldct_combined(args.extracted_dir)
        else:
            data = load_mz_combined(args.extracted_dir)
        year_over_year_comparison(data, args.year1, args.year2, args.type)
    
    elif args.command == "spot-check":
        if args.type == "ldct":
            data = load_ldct_combined(args.extracted_dir)
        else:
            data = load_mz_combined(args.extracted_dir)
        spot_check_county(data, args.county)
    
    elif args.command == "full":
        if args.zone_type == "ldct":
            data = load_ldct_combined(args.extracted_dir)
        else:
            data = load_mz_combined(args.extracted_dir)
        
        summary_stats(data, args.zone_type)
        find_anomalies(data)
        consistency_check(data)
        
        # Compare consecutive years
        years = sorted(data.keys())
        for i in range(len(years) - 1):
            year_over_year_comparison(data, years[i], years[i+1], args.zone_type)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

