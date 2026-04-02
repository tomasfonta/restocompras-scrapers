"""Validate items from JSON file or dry-run results."""

import sys
import argparse
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def validate_items_file(items_file: Path, strict: bool = False) -> int:
    
    if not items_file.exists():
        logger.error(f"File not found: {items_file}")
        return 1
    
    try:
        with open(items_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        return 1
    
    # Extract items from data
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and 'items' in data:
        items = data['items']
    elif isinstance(data, dict):
        items = [data]
    else:
        logger.error("Invalid data format")
        return 1
    
    logger.info(f"Found {len(items)} items to validate\n")
    
    # Validate
    validator = ItemValidator(strict_mode=strict)
    report = validator.validate_batch(items)
    
    # Print report
    logger.info(validator.print_report(report))
    
    # Summary
    logger.info("="*70)
    
    if report['invalid_items'] == 0:
        logger.info("✅ All items are valid!")
        return 0
    else:
        logger.warning(f"⚠️  {report['invalid_items']} items are invalid")
        return 1


def validate_scraped_products(supplier_name: str, config_dir: Path, 
                             output_dir: Path, strict: bool = False) -> int:
    """
    Validate items from a dry-run test result.
    
    Args:
        supplier_name: Name of supplier
        config_dir: Path to configs
        output_dir: Path to output directory
        strict: Treat warnings as errors
        
    Returns:
        Exit code
    """
    # Find most recent dry-run results
    results_file = output_dir / f'{supplier_name}_dry_run_results.json'
    
    if not results_file.exists():
        logger.error(f"No dry-run results found for {supplier_name}")
        logger.info(f"Expected: {results_file}")
        return 1
    
    logger.info(f"Validating items from: {results_file}\n")
    
    return validate_items_file(results_file, strict=strict)


def main():
    """Command-line interface for validating items."""
    parser = argparse.ArgumentParser(
        description='Validate items from dry-run results or custom JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate items from file
  python3 skills/validate.py items.json
  
  # Validate from dry-run results
  python3 skills/validate.py --supplier greenshop
  
  # Strict mode (treat warnings as errors)
  python3 skills/validate.py items.json --strict
  
  # From custom output directory
  python3 skills/validate.py \\
    --supplier greenshop \\
    --output-dir ./test-results
        """
    )
    
    parser.add_argument(
        'file',
        nargs='?',
        help='JSON file with items to validate'
    )
    parser.add_argument(
        '--supplier',
        help='Validate items from dry-run results for this supplier'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('./output'),
        help='Path to output directory (for --supplier mode)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.file and not args.supplier:
        parser.error("Either provide a file path or use --supplier")
    
    if args.file and args.supplier:
        parser.error("Cannot use both file and --supplier")
    
    # Run validation
    if args.file:
        exit_code = validate_items_file(Path(args.file), strict=args.strict)
    else:
        exit_code = validate_scraped_products(
            supplier_name=args.supplier,
            config_dir=Path('./configs'),
            output_dir=args.output_dir,
            strict=args.strict
        )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
