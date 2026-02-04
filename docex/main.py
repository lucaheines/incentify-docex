"""
Main CLI for docex - Georgia Tax Incentive Zone PDF Extractor.

Usage:
    python -m docex.main extract-all data_folders/
    python -m docex.main extract-ldct data_folders/GA_less_dev_cencus/
    python -m docex.main extract-mz data_folders/GA_military_zones/
    python -m docex.main extract-oz data_folders/GA_opportunity_zones/
"""

import argparse
import json
from pathlib import Path
from datetime import date

from .extractors.ldct import LDCTExtractor
from .extractors.military_zone import MilitaryZoneExtractor
from .extractors.opportunity_zone import OpportunityZoneExtractor


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def extract_ldct(input_dir: Path, output_dir: Path) -> dict:
    """Extract all LDCT files from a directory."""
    print(f"\n{'='*60}")
    print("Extracting Less Developed Census Tracts (LDCT)")
    print(f"{'='*60}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    all_records = []
    combined = {}
    
    for pdf_file in sorted(input_dir.glob("*.pdf")):
        print(f"\nProcessing: {pdf_file.name}")
        
        extractor = LDCTExtractor()
        try:
            records = extractor.extract(pdf_file)
            print(f"  Extracted {len(records)} records")
            
            if records:
                all_records.extend(records)
                year_dict = extractor.to_simple_dict()
                
                # Save per-year file
                for year, data in year_dict.items():
                    year_file = output_dir / f"ldct_{year}.json"
                    with open(year_file, "w") as f:
                        json.dump(data, f, indent=2, default=json_serial)
                    print(f"  Saved: {year_file.name}")
                    
                    # Add to combined
                    combined[year] = data
            else:
                print("  WARNING: No records extracted (may be scanned/image PDF)")
                
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Save combined file
    if combined:
        combined_file = output_dir / "ldct_combined.json"
        with open(combined_file, "w") as f:
            json.dump(combined, f, indent=2, default=json_serial)
        print(f"\nSaved combined: {combined_file}")
    
    print(f"\nTotal LDCT records: {len(all_records)}")
    return combined


def extract_mz(input_dir: Path, output_dir: Path) -> dict:
    """Extract all Military Zone files from a directory."""
    print(f"\n{'='*60}")
    print("Extracting Military Zones (MZ)")
    print(f"{'='*60}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    all_records = []
    combined = {}
    
    for pdf_file in sorted(input_dir.glob("*.pdf")):
        print(f"\nProcessing: {pdf_file.name}")
        
        extractor = MilitaryZoneExtractor()
        try:
            records = extractor.extract(pdf_file)
            print(f"  Extracted {len(records)} records")
            
            if records:
                all_records.extend(records)
                year_dict = extractor.to_dict()
                
                # Save per-year file
                for year, data in year_dict.items():
                    year_file = output_dir / f"mz_{year}.json"
                    with open(year_file, "w") as f:
                        json.dump(data, f, indent=2, default=json_serial)
                    print(f"  Saved: {year_file.name}")
                    
                    # Add to combined
                    if year not in combined:
                        combined[year] = {}
                    for county, tracts in data.items():
                        if county not in combined[year]:
                            combined[year][county] = []
                        combined[year][county].extend(tracts)
            else:
                print("  WARNING: No records extracted (may be a map visualization)")
                
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Save combined file
    if combined:
        combined_file = output_dir / "mz_combined.json"
        with open(combined_file, "w") as f:
            json.dump(combined, f, indent=2, default=json_serial)
        print(f"\nSaved combined: {combined_file}")
    
    print(f"\nTotal MZ records: {len(all_records)}")
    return combined


def extract_oz(input_dir: Path, output_dir: Path) -> list:
    """Extract all Opportunity Zone files from a directory."""
    print(f"\n{'='*60}")
    print("Extracting State Opportunity Zones (OZ)")
    print(f"{'='*60}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    all_records = []
    
    for pdf_file in sorted(input_dir.glob("*.pdf")):
        print(f"\nProcessing: {pdf_file.name}")
        
        extractor = OpportunityZoneExtractor()
        try:
            records = extractor.extract(pdf_file)
            print(f"  Extracted {len(records)} records")
            
            if records:
                all_records.extend(extractor.to_dict())
                
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Save output
    if all_records:
        output_file = output_dir / "opportunity_zones.json"
        with open(output_file, "w") as f:
            json.dump(all_records, f, indent=2, default=json_serial)
        print(f"\nSaved: {output_file}")
    
    print(f"\nTotal OZ records: {len(all_records)}")
    return all_records


def extract_all(data_dir: Path):
    """Extract from all zone type folders."""
    print("\n" + "="*60)
    print("Georgia Tax Incentive Zone Extractor")
    print("="*60)
    
    # LDCT
    ldct_dir = data_dir / "GA_less_dev_cencus"
    if ldct_dir.exists():
        ldct_output = ldct_dir / "extracted"
        extract_ldct(ldct_dir, ldct_output)
    else:
        print(f"LDCT directory not found: {ldct_dir}")
    
    # Military Zones
    mz_dir = data_dir / "GA_military_zones"
    if mz_dir.exists():
        mz_output = mz_dir / "extracted"
        extract_mz(mz_dir, mz_output)
    else:
        print(f"MZ directory not found: {mz_dir}")
    
    # Opportunity Zones
    oz_dir = data_dir / "GA_opportunity_zones"
    if oz_dir.exists():
        oz_output = oz_dir / "extracted"
        extract_oz(oz_dir, oz_output)
    else:
        print(f"OZ directory not found: {oz_dir}")
    
    print("\n" + "="*60)
    print("Extraction complete!")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Georgia Tax Incentive Zone PDF Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m docex.main extract-all data_folders/
  python -m docex.main extract-ldct data_folders/GA_less_dev_cencus/
  python -m docex.main extract-mz data_folders/GA_military_zones/
  python -m docex.main extract-oz data_folders/GA_opportunity_zones/
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # extract-all command
    p_all = subparsers.add_parser("extract-all", help="Extract all zone types")
    p_all.add_argument("data_dir", type=Path, help="Root data directory")
    
    # extract-ldct command
    p_ldct = subparsers.add_parser("extract-ldct", help="Extract LDCT files")
    p_ldct.add_argument("input_dir", type=Path, help="Directory with LDCT PDFs")
    p_ldct.add_argument("--output", "-o", type=Path, help="Output directory")
    
    # extract-mz command
    p_mz = subparsers.add_parser("extract-mz", help="Extract Military Zone files")
    p_mz.add_argument("input_dir", type=Path, help="Directory with MZ PDFs")
    p_mz.add_argument("--output", "-o", type=Path, help="Output directory")
    
    # extract-oz command
    p_oz = subparsers.add_parser("extract-oz", help="Extract Opportunity Zone files")
    p_oz.add_argument("input_dir", type=Path, help="Directory with OZ PDFs")
    p_oz.add_argument("--output", "-o", type=Path, help="Output directory")
    
    args = parser.parse_args()
    
    if args.command == "extract-all":
        extract_all(args.data_dir)
    elif args.command == "extract-ldct":
        output = args.output or args.input_dir / "extracted"
        extract_ldct(args.input_dir, output)
    elif args.command == "extract-mz":
        output = args.output or args.input_dir / "extracted"
        extract_mz(args.input_dir, output)
    elif args.command == "extract-oz":
        output = args.output or args.input_dir / "extracted"
        extract_oz(args.input_dir, output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

