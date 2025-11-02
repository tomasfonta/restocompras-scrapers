#!/usr/bin/env python3
"""
restoCompras Scrapers - Run All Suppliers

This script runs scrapers for all available suppliers sequentially
and provides a detailed summary of the results.
"""

import argparse
import subprocess
import sys
from datetime import datetime
from typing import List, Tuple

# ANSI color codes
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
RESET = '\033[0m'


# List of all suppliers
SUPPLIERS = [
    "greenshop",
    "lacteos_granero", 
    "distribuidora_pop",
    "tyna",
    "piala",
    "distribuidora_demarchi",
    "laduvalina",
    "labebidadetusfiestas"
]


def run_supplier(supplier_name: str, environment: str = 'dev') -> bool:
    """
    Run scraper for a single supplier.
    
    Args:
        supplier_name: Name of the supplier to scrape
        environment: Environment to use ('dev' or 'prod')
        
    Returns:
        True if successful, False otherwise
    """
    print()
    print("-" * 71)
    print(f"{YELLOW}Running scraper for: {supplier_name} (env: {environment}){RESET}")
    print("-" * 71)
    
    try:
        # Run the scraper as a subprocess with environment argument
        result = subprocess.run(
            ['python3', 'main.py', supplier_name, '--env', environment],
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        # Check exit code
        if result.returncode == 0:
            print(f"{GREEN}✓ {supplier_name} completed successfully{RESET}")
            return True
        else:
            print(f"{RED}✗ {supplier_name} failed with exit code {result.returncode}{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}✗ {supplier_name} failed with error: {e}{RESET}")
        return False


def main():
    """Main function to run all suppliers."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run scrapers for all configured suppliers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all suppliers in development environment (localhost)
  python3 run_all_suppliers.py
  python3 run_all_suppliers.py --env dev
  
  # Run all suppliers in production environment
  python3 run_all_suppliers.py --env prod
        """
    )
    
    parser.add_argument(
        '--env', '--environment',
        dest='environment',
        choices=['dev', 'prod'],
        default='dev',
        help='Environment to use: dev (localhost) or prod (production server). Default: dev'
    )
    
    args = parser.parse_args()
    environment = args.environment
    
    # Track results
    successful_suppliers: List[str] = []
    failed_suppliers: List[str] = []
    
    # Print header
    print("=" * 71)
    print(f"{BLUE}restoCompras Scrapers - Running All Suppliers{RESET}")
    print("=" * 71)
    print(f"Environment: {YELLOW}{environment.upper()}{RESET}")
    print(f"Total suppliers to scrape: {len(SUPPLIERS)}")
    start_time = datetime.now()
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 71)
    
    # Run each supplier
    for supplier in SUPPLIERS:
        success = run_supplier(supplier, environment)
        
        if success:
            successful_suppliers.append(supplier)
        else:
            failed_suppliers.append(supplier)
        
        print()
    
    # Calculate duration
    end_time = datetime.now()
    duration = end_time - start_time
    
    # Print summary
    print()
    print("=" * 71)
    print(f"{BLUE}SCRAPING SUMMARY{RESET}")
    print("=" * 71)
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print()
    print(f"Total suppliers: {len(SUPPLIERS)}")
    print(f"{GREEN}Successful: {len(successful_suppliers)}{RESET}")
    print(f"{RED}Failed: {len(failed_suppliers)}{RESET}")
    print()
    
    # Show successful suppliers
    if successful_suppliers:
        print(f"{GREEN}Successful suppliers:{RESET}")
        for supplier in successful_suppliers:
            print(f"  ✓ {supplier}")
        print()
    
    # Show failed suppliers
    if failed_suppliers:
        print(f"{RED}Failed suppliers:{RESET}")
        for supplier in failed_suppliers:
            print(f"  ✗ {supplier}")
        print()
    
    print("Output files saved to: output/")
    print("Log files saved to: logs/")
    print("=" * 71)
    
    # Exit with appropriate code
    sys.exit(0 if not failed_suppliers else 1)


if __name__ == '__main__':
    main()
