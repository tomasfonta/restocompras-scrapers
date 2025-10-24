"""Lácteos Granero scraper implementation."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium.webdriver.common.by import By

from ..core.scraper_base import ScraperBase
from ..core.parser import DataParser
from ..strategies import SeleniumStrategy


class LacteosGraneroScraper(ScraperBase):
    """
    Scraper for Lácteos Granero website using Selenium strategy.
    
    Lácteos Granero loads content dynamically with JavaScript,
    so we need Selenium to render the page fully.
    """
    
    def __init__(self, config: Dict[str, Any], api_client: 'APIClient'):
        """
        Initialize Lácteos Granero scraper.
        
        Args:
            config: Supplier configuration
            api_client: API client instance
        """
        super().__init__(config, api_client)
        
        # Initialize scraping strategy
        strategy_config = config.get('strategy_config', {})
        self.strategy = SeleniumStrategy(strategy_config)
        
        # Get selectors from config
        self.selectors = config.get('selectors', {})
        
        # Initialize parser
        self.parser = DataParser()
    
    def get_urls(self) -> List[str]:
        """Get list of URLs to scrape from configuration."""
        return self.config.get('urls', [])
    
    def _fetch_html(self, url: str) -> str:
        """
        Fetch HTML using Selenium strategy.
        
        Waits for product elements to load before returning.
        """
        # Navigate to URL
        self.strategy.driver.get(url)
        
        # Wait for products to load
        product_selector = self.selectors.get('product_list', '.product')
        try:
            self.strategy.wait_for_element(product_selector, By.CSS_SELECTOR)
        except Exception as e:
            self.logger.warning(f"Timeout waiting for products: {e}")
        
        # Scroll to load all dynamic content
        self.strategy._scroll_page()
        
        # Get rendered HTML
        return self.strategy.driver.page_source
    
    def extract_products(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        """
        Extract products from Lácteos Granero HTML.
        
        Args:
            html_content: Rendered HTML content from Selenium
            url: Source URL (for constructing image URLs)
            
        Returns:
            List of product dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all product items
        product_selector = self.selectors.get('product_list', '.product')
        product_items = soup.select(product_selector)
        
        if not product_items:
            self.logger.warning(f"No products found with selector '{product_selector}'")
            return []
        
        self.logger.info(f"Found {len(product_items)} product elements")
        
        products = []
        
        for item in product_items:
            try:
                product = self._extract_single_product(item, url)
                
                # Filter out invalid products
                if product and product.get('price', 0) > 0:
                    products.append(product)
                    
            except Exception as e:
                self.logger.error(f"Error extracting product: {e}", exc_info=True)
                continue
        
        return products
    
    def _extract_single_product(self, item: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        Extract data from a single product element.
        
        Args:
            item: BeautifulSoup element for product
            base_url: Base URL for constructing image URLs
            
        Returns:
            Product dictionary or None if invalid
        """
        # Extract title
        title_selector = self.selectors.get('title', '.product__details__top__name')
        title_tag = item.select_one(title_selector)
        full_title = title_tag.text.strip() if title_tag else "N/A"
        
        if full_title == "N/A":
            return None
        
        # Parse title into name, quantity, unit
        name, quantity, unit = self.parser.parse_product_title(full_title)
        
        # Extract price
        price_selector = self.selectors.get('price', '.product__details__price--legacy__current--legacy')
        price_tag = item.select_one(price_selector)
        price_text = price_tag.text.strip() if price_tag else "$0"
        
        price, _ = self.parser.clean_price(price_text)
        
        if price == 0.0:
            return None
        
        # Extract image
        image_selector = self.selectors.get('image', '.image-gallery-image')
        img_tag = item.select_one(image_selector)
        image_url = ""
        
        if img_tag:
            image_url = img_tag.get('src', '')
            
            # Convert relative URLs to absolute
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(base_url, image_url)
        
        # Build product dictionary
        product = {
            'name': name,
            'brand': self.config['supplier_name'],
            'description': name,
            'price': price,
            'image': image_url,
            'unit': unit,
            'quantity': quantity,
            'supplierId': self.config['supplier_id']
        }
        
        return product
    
    def __del__(self):
        """Clean up strategy resources."""
        if hasattr(self, 'strategy'):
            self.strategy.close()
