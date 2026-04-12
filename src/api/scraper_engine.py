"""
Scraper Engine for API endpoints.

Orchestrates scraping execution without persistence operations.
Returns raw items without saving to database or Excel files.
"""
import logging
from typing import List, Dict, Any, Tuple

from src.config import ConfigLoader
from src.core import APIClient
from src.utils import setup_logger


# Import all scraper classes
from src.suppliers import (
    GreenShopScraper, LacteosGraneroScraper, DistribuidoraPopScraper, 
    TYNAScraper, PialaScraper, DistribuidoraDeMarchiScraper, 
    LaduvalinaScraper, LaBebidaDeTusFiestasScraper,
    IrlandaScraper, ElChanarCarnesScraper
)


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
    'irlanda': IrlandaScraper,
    'el_chanar_carnes': ElChanarCarnesScraper,
}


def get_available_suppliers() -> List[str]:
    """
    Get list of available supplier names.
    
    Returns:
        List of supplier names
    """
    return list(SCRAPER_REGISTRY.keys())


def scrape_supplier_only(supplier_name: str, config_dir: str = 'configs',
                        log_dir: str = 'logs', environment: str = 'dev',
                        logger: logging.Logger = None) -> Tuple[bool, Any]:
    """
    Execute scraping for a supplier WITHOUT persistence.
    
    Returns items directly without saving to database or Excel.
    Suitable for API endpoints that stream results.
    
    Args:
        supplier_name: Name of supplier to scrape
        config_dir: Path to configuration directory
        log_dir: Path to logs directory
        environment: 'dev' or 'prod'
        logger: Optional logger instance. Creates one if not provided.
        
    Returns:
        Tuple of (success: bool, data: Dict with items or error details)
        
    Success response:
        (True, {
            'status': 'success',
            'supplier': supplier_name,
            'supplier_id': <id>,
            'item_count': <count>,
            'items': [...]
        })
        
    Error response:
        (False, {
            'status': 'error',
            'code': 'error_type',
            'error': 'error message'
        })
    """
    if logger is None:
        logger = setup_logger(log_dir=log_dir)
    
    try:
        # Validate supplier exists
        if supplier_name not in SCRAPER_REGISTRY:
            logger.error(f"Supplier not found: {supplier_name}")
            return False, {
                'status': 'error',
                'code': 'supplier_not_found',
                'error': f"Supplier '{supplier_name}' not available",
                'available_suppliers': list(SCRAPER_REGISTRY.keys())
            }
        
        logger.info(f"Starting scrape for API endpoint: {supplier_name}")
        logger.info(f"Environment: {environment.upper()}")
        
        # Load configurations
        config_loader = ConfigLoader(config_dir, environment=environment)
        
        # Load API config
        api_config = config_loader.load_api_config()
        api_client = APIClient(api_config)
        
        # Authenticate with backend API using admin credentials
        logger.info("Authenticating with backend API...")
        auth_token = api_client.login_with_credentials('admin@test.com', '123123')
        if not auth_token:
            logger.error("Failed to authenticate with backend API. Scraping cannot proceed.")
            return False, {
                'status': 'error',
                'code': 'auth_failed',
                'error': 'Failed to authenticate with backend API'
            }
        logger.info("✅ Authentication successful")
        
        # Load supplier config
        supplier_config = config_loader.load_supplier_config(supplier_name)
        logger.info(f"Loaded config for: {supplier_config.get('supplier_name', supplier_name)}")
        
        # Get scraper class
        scraper_class = SCRAPER_REGISTRY[supplier_name]
        logger.info(f"Initializing scraper: {scraper_class.__name__}")
        
        # Initialize scraper
        scraper = scraper_class(supplier_config, api_client)
        
        # Execute scraping WITHOUT posting to API (items only for return)
        logger.info(f"Executing scrape for {supplier_name}...")
        items = scraper.scrape_items_only()
        
        if items is None:
            items = []
        
        item_count = len(items)
        logger.info(f"Scraping completed. Items found: {item_count}")
        
        # Return items without persistence
        return True, {
            'status': 'success',
            'supplier': supplier_name,
            'supplier_id': supplier_config.get('supplier_id'),
            'supplier_name': supplier_config.get('supplier_name', supplier_name),
            'item_count': item_count,
            'items': items if items else []
        }
        
    except FileNotFoundError as e:
        logger.error(f"Configuration not found: {e}")
        return False, {
            'status': 'error',
            'code': 'config_not_found',
            'error': str(e)
        }
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        return False, {
            'status': 'error',
            'code': 'scrape_failed',
            'error': str(e)
        }
