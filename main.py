"""Main entry point for the restoCompras scraper system."""

import argparse
import sys
from typing import Optional

from src.config import ConfigLoader
from src.core import APIClient, DataExporter
from src.suppliers import GreenShopScraper, LacteosGraneroScraper, DistribuidoraPopScraper, TYNAScraper
from src.utils import setup_logger


# Mapping of supplier names to scraper classes
SCRAPER_REGISTRY = {
    'greenshop': GreenShopScraper,
    'lacteos_granero': LacteosGraneroScraper,
    'distribuidora_pop': DistribuidoraPopScraper,
    'tyna': TYNAScraper,
}


def run_scraper(supplier_name: str, config_dir: str = 'configs', 
                output_dir: str = 'output', log_dir: str = 'logs') -> bool:
    """
    Run scraper for a specific supplier.
    
    Args:
        supplier_name: Name of supplier to scrape
        config_dir: Configuration directory path
        output_dir: Output directory for exports
        log_dir: Directory for log files
        
    Returns:
        True if successful, False otherwise
    """
    # Set up logging
    logger = setup_logger(log_dir=log_dir)
    
    try:
        # Load configurations
        logger.info(f"Starting scraper for: {supplier_name}")
        
        config_loader = ConfigLoader(config_dir)
        
        # Load API config
        api_config = config_loader.load_api_config()
        api_client = APIClient(api_config)
        
        # Load supplier config
        supplier_config = config_loader.load_supplier_config(supplier_name)
        
        # Get appropriate scraper class
        scraper_class = SCRAPER_REGISTRY.get(supplier_name)
        
        if scraper_class is None:
            logger.error(f"No scraper implementation found for '{supplier_name}'")
            logger.info(f"Available scrapers: {', '.join(SCRAPER_REGISTRY.keys())}")
            return False
        
        # Initialize scraper
        scraper = scraper_class(supplier_config, api_client)
        
        # Run scraping process
        logger.info("="*70)
        logger.info(f"STARTING SCRAPE: {supplier_config['supplier_name']}")
        logger.info("="*70)
        
        products = scraper.scrape()
        
        if not products:
            logger.warning("No products were successfully scraped")
            return False
        
        # Export results
        exporter = DataExporter(output_dir)
        
        excel_file = exporter.export_to_excel(products, supplier_config['supplier_name'])
        
        if excel_file:
            logger.info("="*70)
            logger.info("SCRAPING COMPLETED SUCCESSFULLY")
            logger.info(f"Total products: {len(products)}")
            logger.info(f"Export file: {excel_file}")
            logger.info("="*70)
            return True
        else:
            logger.error("Failed to export results")
            return False
            
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        return False
    except Exception as e:
        logger.error(f"Scraper failed with error: {e}", exc_info=True)
        return False


def list_suppliers(config_dir: str = 'configs') -> None:
    """
    List all available supplier configurations.
    
    Args:
        config_dir: Configuration directory path
    """
    config_loader = ConfigLoader(config_dir)
    suppliers = config_loader.list_suppliers()
    
    print("\nAvailable suppliers:")
    print("-" * 40)
    
    if not suppliers:
        print("No supplier configurations found.")
        print(f"Add .json files to: {config_dir}/suppliers/")
    else:
        for supplier in suppliers:
            status = "✓" if supplier in SCRAPER_REGISTRY else "⚠"
            impl_note = "" if supplier in SCRAPER_REGISTRY else " (no implementation)"
            print(f"{status} {supplier}{impl_note}")
    
    print("-" * 40)
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='restoCompras Web Scraper - Extract product data from food suppliers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Scrape Green Shop
  python main.py greenshop
  
  # Scrape Lácteos Granero
  python main.py lacteos_granero
  
  # List available suppliers
  python main.py --list
  
  # Use custom config directory
  python main.py greenshop --config-dir ./my_configs
        '''
    )
    
    parser.add_argument(
        'supplier',
        nargs='?',
        help='Name of supplier to scrape (e.g., greenshop, lacteos_granero)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available suppliers'
    )
    
    parser.add_argument(
        '--config-dir',
        default='configs',
        help='Configuration directory (default: configs)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory for exports (default: output)'
    )
    
    parser.add_argument(
        '--log-dir',
        default='logs',
        help='Log directory (default: logs)'
    )
    
    args = parser.parse_args()
    
    # Handle list command
    if args.list:
        list_suppliers(args.config_dir)
        return
    
    # Require supplier argument if not listing
    if not args.supplier:
        parser.print_help()
        print("\nError: supplier argument is required (or use --list)")
        sys.exit(1)
    
    # Run scraper
    success = run_scraper(
        args.supplier,
        config_dir=args.config_dir,
        output_dir=args.output_dir,
        log_dir=args.log_dir
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
