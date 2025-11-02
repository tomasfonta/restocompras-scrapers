"""Main entry point for the restoCompras scraper system."""

import argparse
import logging
import sys
from typing import Optional

from src.config import ConfigLoader
from src.core import APIClient, DataExporter
from src.suppliers import GreenShopScraper, LacteosGraneroScraper, DistribuidoraPopScraper, TYNAScraper, PialaScraper, DistribuidoraDeMarchiScraper, LaduvalinaScraper, LaBebidaDeTusFiestasScraper
from src.utils import setup_logger


# Mapping of supplier names to scraper classes
SCRAPER_REGISTRY = {
    'greenshop': GreenShopScraper,
    'lacteos_granero': LacteosGraneroScraper,
    'distribuidora_pop': DistribuidoraPopScraper,
    'tyna': TYNAScraper,
    'piala': PialaScraper,
    'distribuidora_demarchi': DistribuidoraDeMarchiScraper,
    'laduvalina': LaduvalinaScraper,
    'labebidadetusfiestas': LaBebidaDeTusFiestasScraper,
}


def run_scraper(supplier_name: str, config_dir: str = 'configs', 
                output_dir: str = 'output', log_dir: str = 'logs',
                environment: str = 'dev') -> bool:
    """
    Run scraper for a specific supplier.
    
    Args:
        supplier_name: Name of supplier to scrape
        config_dir: Configuration directory path
        output_dir: Output directory for exports
        log_dir: Directory for log files
        environment: Environment to use ('dev' or 'prod'). Default is 'dev'.
        
    Returns:
        True if successful, False otherwise
    """
    # Set up logging with DEBUG level for file handler
    logger = setup_logger(log_dir=log_dir, level=logging.DEBUG)
    
    try:
        # Load configurations
        logger.info(f"Starting scraper for: {supplier_name}")
        logger.info(f"Environment: {environment.upper()}")
        
        config_loader = ConfigLoader(config_dir, environment=environment)
        
        # Load API config (will use environment-specific config)
        api_config = config_loader.load_api_config()
        logger.info(f"API Base URL: {api_config.get('base_url')}")
        api_client = APIClient(api_config)
        
        # Load supplier config first to check for supplier-specific credentials
        supplier_config = config_loader.load_supplier_config(supplier_name)
        
        # Perform login to get fresh token
        logger.info("="*70)
        logger.info("AUTHENTICATING WITH BACKEND API")
        logger.info("="*70)
        
        token = None
        
        # Check if supplier has its own credentials
        supplier_credentials = supplier_config.get('credentials')

        logger.info(f"Supplier credentials: {supplier_credentials}")

        email = supplier_config.get('credentials').get('name');
        password = supplier_config.get('credentials').get('password');

        logger.info(f"Using supplier name: {email} {password}")
        
        if email and password:
            logger.info(f"Using supplier-specific credentials for {supplier_name}")
      
            token = api_client.login_with_credentials(
                supplier_credentials['name'],
                supplier_credentials['password']
            )
        
        if token:
            # Update config file with new token
            config_loader.update_auth_token(token)
            logger.info("Authentication successful - token updated in config")
            
            # Fetch supplier details from backend
            if email:
                logger.info("="*70)
                logger.info("FETCHING SUPPLIER DETAILS")
                logger.info("="*70)
                
                supplier_details = api_client.fetch_supplier_details(email=email)
                
                if supplier_details:
                    # Extract supplier information from backend
                    backend_supplier_id = supplier_details.get('id') or supplier_details.get('supplierId')
                    backend_supplier_name = supplier_details.get('name') or supplier_details.get('supplierName')
                    
                    if backend_supplier_id:
                        logger.info(f"Backend supplier ID: {backend_supplier_id}")
                        supplier_config['supplier_id'] = backend_supplier_id
                    else:
                        logger.error("Supplier details retrieved but no ID found. Aborting.")
                        return False
                    
                    if backend_supplier_name:
                        logger.info(f"Backend supplier name: {backend_supplier_name}")
                        supplier_config['supplier_name'] = backend_supplier_name
                    else:
                        # Fallback to formatted supplier_name parameter if no name in backend
                        supplier_config['supplier_name'] = email
                    
                    # Store full supplier details for potential future use
                    supplier_config['supplier_details'] = supplier_details
                    
                    # Clean database before scraping
                    logger.info("="*70)
                    logger.info("CLEANING DATABASE")
                    logger.info("="*70)
                    
                    if api_client.delete_supplier_items(backend_supplier_id):
                        logger.info("Database cleaned successfully - ready to scrape fresh data")
                    else:
                        logger.warning("Failed to clean database, but continuing with scrape...")
                else:
                    logger.error(f"Could not fetch supplier details for {email}. Aborting.")
                    logger.error("Supplier ID and name are required from backend.")
                    return False
            else:
                logger.error("No supplier email available for fetching details. Aborting.")
                return False
        else:
            logger.error("Authentication failed - proceeding with existing token")
            # If login fails and there's no token, we should abort
            if not api_config.get('auth_token'):
                logger.error("No valid authentication token available. Aborting.")
                return False
        
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
  # Scrape Green Shop (development)
  python main.py greenshop
  
  # Scrape in production environment
  python main.py greenshop --env prod
  
  # Scrape Lácteos Granero in production
  python main.py lacteos_granero --env prod
  
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
        '--env',
        '--environment',
        dest='environment',
        choices=['dev', 'prod'],
        default='dev',
        help='Environment to use: dev (localhost) or prod (production server). Default: dev'
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
        log_dir=args.log_dir,
        environment=args.environment
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
