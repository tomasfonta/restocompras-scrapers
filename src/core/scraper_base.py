"""Base scraper class defining the common interface for all scrapers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging


class ScraperBase(ABC):
    """
    Abstract base class for all supplier scrapers.
    
    Defines the common interface and workflow that all scrapers must implement.
    Each supplier scraper should inherit from this class and implement the
    abstract methods according to their specific website structure.
    """
    
    def __init__(self, config: Dict[str, Any], api_client: 'APIClient'):
        """
        Initialize the scraper with configuration and API client.
        
        Args:
            config: Supplier-specific configuration dictionary
            api_client: Shared API client for backend communication
        """
        self.config = config
        self.api_client = api_client
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate that required configuration keys are present."""
        required_keys = ['supplier_id', 'supplier_name', 'scraping_strategy']
        missing_keys = [key for key in required_keys if key not in self.config]
        
        if missing_keys:
            raise ValueError(f"Missing required config keys: {missing_keys}")
    
    @abstractmethod
    def get_urls(self) -> List[str]:
        """
        Return list of URLs to scrape for this supplier.
        
        Returns:
            List of URLs to process
        """
        pass
    
    @abstractmethod
    def extract_products(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        """
        Extract product data from HTML content.
        
        Args:
            html_content: Raw HTML content from the page
            url: The URL that was scraped (for context/images)
            
        Returns:
            List of product dictionaries with raw extracted data
        """
        pass
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping workflow orchestrator.
        
        Returns:
            List of successfully processed products ready for export
        """
        self.logger.info(f"Starting scrape for {self.config['supplier_name']}")
        
        all_products = []
        urls = self.get_urls()
        
        for url in urls:
            self.logger.info(f"Scraping URL: {url}")
            try:
                # Get HTML using the appropriate strategy
                html_content = self._fetch_html(url)
                
                # Extract products from HTML
                products = self.extract_products(html_content, url)
                all_products.extend(products)
                
                self.logger.info(f"Extracted {len(products)} products from {url}")
            except Exception as e:
                self.logger.error(f"Failed to scrape {url}: {e}", exc_info=True)
                continue
        
        self.logger.info(f"Total products extracted: {len(all_products)}")
        
        # Process and deduplicate        
        processed_products = self._process_products(all_products)
        
        # Fetch product IDs and post to API
        final_products = self._integrate_with_api(processed_products)

        return final_products

    @abstractmethod
    def _fetch_html(self, url: str) -> str:
        """
        Fetch HTML content using the appropriate scraping strategy.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string
        """
        pass
    
    def _process_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process and deduplicate products.
        
        Args:
            products: Raw product list
            
        Returns:
            Deduplicated and standardized product list
        """
        from ..utils.text_processing import deduplicate_products
        
        self.logger.info(f"Processing {len(products)} products...")
        deduplicated = deduplicate_products(products)
        removed = len(products) - len(deduplicated)
        
        if removed > 0:
            self.logger.info(f"Removed {removed} duplicate products")
        
        return deduplicated
    
    def _integrate_with_api(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetch product IDs and post to API.
        
        Args:
            products: Processed product list
            
        Returns:
            Products successfully posted to API
        """
        self.logger.info(f"Integrating {len(products)} products with API...")
        
        successful_products = []
        
        for product in products:
            product_name = product.get('name')
            
            # Fetch product ID from API
            product_id = self.api_client.fetch_product_id(product_name)
            
            if product_id is None:
                self.logger.warning(f"Skipping {product_name}: No product ID found")
                continue
            
            product['productId'] = product_id
            
            # Post to API
            if self.api_client.post_item(product):
                successful_products.append(product)
        
        self.logger.info(f"Successfully posted {len(successful_products)} products to API")
        return successful_products
    
    def get_supplier_id(self) -> int:
        """Get the supplier ID from configuration."""
        return self.config['supplier_id']
    
    def get_supplier_name(self) -> str:
        """Get the supplier name from configuration."""
        return self.config['supplier_name']
