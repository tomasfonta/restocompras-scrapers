"""Base scraper class defining the common interface for all scrapers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
from .item_builder import ItemBuilder


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
        
        # Initialize ItemBuilder for configuration-driven item creation
        self.item_builder = ItemBuilder(config)
    
    def _validate_config(self) -> None:
        """Validate that required configuration keys are present."""
        required_keys = ['scraping_strategy']
        missing_keys = [key for key in required_keys if key not in self.config]
        
        if missing_keys:
            raise ValueError(f"Missing required config keys: {missing_keys}")
        
        # Set defaults for optional fields
        if 'supplier_id' not in self.config:
            self.config['supplier_id'] = 0
        if 'supplier_name' not in self.config:
            self.config['supplier_name'] = 'Unknown Supplier'
    
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

    def scrape_items_only(self) -> List[Dict[str, Any]]:
        """
        Scrape and extract items WITHOUT posting to API.
        
        Used by API endpoints that return items directly without persistence.
        
        Returns:
            List of items ready for return (without API posting)
        """
        self.logger.info(f"Starting item extraction (no API posting) for {self.config['supplier_name']}")
        
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
        
        # Build items using ItemBuilder without posting to API
        items = self._build_items_only(processed_products)
        
        self.logger.info(f"Successfully built {len(items)} items for return")
        return items

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
        Fetch product IDs, build items using ItemBuilder, and post to API.
        
        Args:
            products: Processed product list
            
        Returns:
            Products successfully posted to API
        """
        self.logger.info(f"Integrating {len(products)} products with API...")
        
        successful_products = []
        failed_products = []
        
        for product in products:
            product_name = product.get('name')
            
            # Fetch product ID from API
            product_id = self.api_client.fetch_product_id(product_name)
            
            if product_id is None:
                self.logger.warning(f"Skipping {product_name}: No product ID found")
                failed_products.append({
                    'product': product,
                    'reason': 'No product ID found'
                })
                continue
            
            # Build item using ItemBuilder with supplier-specific transformations
            item = self.item_builder.build_item(product, product_id)
            
            if item is None:
                self.logger.warning(f"Skipping {product_name}: ItemBuilder failed")
                failed_products.append({
                    'product': product,
                    'reason': 'ItemBuilder failed'
                })
                continue
            
            # Post to API (no validation, send directly)
            if self.api_client.post_item(item):
                successful_products.append(item)
            else:
                failed_products.append({
                    'product': product,
                    'reason': 'API post failed'
                })
        
        self.logger.info(
            f"Successfully posted {len(successful_products)} products to API"
        )
        if failed_products:
            self.logger.info(
                f"Failed to post {len(failed_products)} products "
                f"({len(products) - len(successful_products)} total skipped)"
            )
        
        return successful_products
    
    def _build_items_only(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build items from products WITHOUT posting to API.
        
        Fetches product IDs from backend, builds items using ItemBuilder,
        but does NOT post to API endpoint.
        
        Used for API endpoints that return items directly.
        Items are included even if product ID is not found.
        
        Args:
            products: Processed product list
            
        Returns:
            List of built items ready for return (with or without productId)
        """
        self.logger.info(f"Building items from {len(products)} products (fetching IDs, no API posting)...")
        
        items = []
        
        for product in products:
            product_name = product.get('name', 'Unknown Product')
            
            try:
                # Fetch product ID from backend
                product_id = self.api_client.fetch_product_id(product_name)
                
                if product_id is None:
                    self.logger.warning(f"No product ID found for {product_name}, adding item without productId")
                
                # Build item using ItemBuilder with supplier-specific transformations
                # Include item even if product_id is None
                item = self.item_builder.build_item(product, product_id)
                
                if item is None:
                    self.logger.warning(f"Failed to build item for {product_name}: ItemBuilder returned None")
                    continue
                
                items.append(item)
                
            except Exception as e:
                self.logger.error(f"Error building item for {product_name}: {e}")
                continue
        
        self.logger.info(f"Successfully built {len(items)} items")
        return items
    
    def get_supplier_id(self) -> int:
        """Get the supplier ID from configuration."""
        return self.config['supplier_id']
    
    def get_supplier_name(self) -> str:
        """Get the supplier name from configuration."""
        return self.config['supplier_name']
