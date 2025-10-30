from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from ..core.scraper_base import ScraperBase
from ..core.parser import DataParser
from ..strategies import RequestsStrategy


class PialaScraper(ScraperBase):
    """Scraper for Piala de Patria website."""
    
    def __init__(self, config: Dict[str, Any], api_client: 'APIClient'):
        super().__init__(config, api_client)
        
        # Initialize strategy
        strategy_config = config.get('strategy_config', {})
        self.strategy = RequestsStrategy(strategy_config)
        
        # Store selectors and initialize parser
        self.selectors = config.get('selectors', {})
        self.parser = DataParser()
        
        # Base URL for resolving relative paths
        self.base_url = 'https://www.piala.com.ar'
    
    def get_urls(self) -> List[str]:
        """Get list of URLs to scrape from config."""
        return self.config.get('urls', [])
    
    def _fetch_html(self, url: str) -> str:
        """Fetch HTML content using requests strategy."""
        return self.strategy.fetch_html(url)
    
    def extract_products(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        """
        Extract product data from HTML content.
        
        Args:
            html_content: Raw HTML string
            url: Source URL (for resolving relative paths)
            
        Returns:
            List of product dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        # First, try to find the main product grid container (Elementor + JetEngine layout)
        product_grid = soup.select_one('.jet-listing-grid__items')
        
        if product_grid:
            # Find all product items within the grid
            product_items = product_grid.select('.jet-listing-grid__item')
            self.logger.info(f"Found {len(product_items)} product items in JetEngine grid")
        else:
            # Fallback to standard WooCommerce selectors
            product_items = soup.select('li.product')
            if not product_items:
                product_items = soup.select('.product-item, .woocommerce-loop-product, .product')
            self.logger.info(f"Found {len(product_items)} product items (fallback)")
        
        for item in product_items:
            try:
                # Extract title - prioritize Elementor/JetEngine selectors
                title_element = item.select_one('h3.elementor-heading-title a')
                if not title_element:
                    title_element = item.select_one('h3.elementor-heading-title')
                if not title_element:
                    title_element = item.select_one('h2.woocommerce-loop-product__title a')
                if not title_element:
                    title_element = item.select_one('.woocommerce-loop-product__title')
                if not title_element:
                    title_element = item.select_one('h3 a, h3, h2 a, h2')
                if not title_element:
                    title_element = item.select_one('.product-title, .title')
                
                # Extract price - prioritize Elementor/JetEngine selectors
                price_element = item.select_one('.woocommerce-Price-amount')
                if not price_element:
                    price_element = item.select_one('.price .amount, .price')
                if not price_element:
                    price_element = item.select_one('[class*="price"]')
                
                # Extract image - prioritize Elementor/JetEngine selectors
                image_element = item.select_one('.elementor-widget-image img')
                if not image_element:
                    image_element = item.select_one('.attachment-woocommerce_thumbnail')
                if not image_element:
                    image_element = item.select_one('.product-image img, img')
                
                # Validate required fields
                if not title_element or not price_element:
                    self.logger.warning("Missing title or price, skipping product")
                    continue
                
                # Get text content
                title = title_element.get_text(strip=True)
                price_text = price_element.get_text(strip=True)
                
                # Skip empty titles
                if not title:
                    continue
                
                # Parse title into components
                name, quantity, unit = self.parser.parse_product_title(title)
                
                # Clean and convert price using custom format from config
                price_format = self.config.get('price_format', {})
                price, _ = self.parser.clean_price(price_text, price_format)
                
                # Skip if price is invalid
                if price <= 0:
                    self.logger.warning(f"Invalid price for '{title}': {price_text}")
                    continue
                
                # Get image URL (handle relative paths)
                image_url = ''
                if image_element:
                    image_url = image_element.get('src', '') or image_element.get('data-src', '')
                    if image_url and not image_url.startswith('http'):
                        image_url = urljoin(self.base_url, image_url)
                
                # Normalize unit mapping (from TYNA scraper pattern)
                unit_mapping = {
                    'GR': 'G',
                    'GR.': 'G', 
                    'GRAMOS': 'G',
                    'KG': 'KG',
                    'K': 'KG',
                    'KG.': 'KG',
                    'KILOS': 'KG',
                    'KILOGRAMOS': 'KG',
                    'UN': 'UNIT',
                    'UN.': 'UNIT',
                    'UNIDAD': 'UNIT',
                    'UNIDADES': 'UNIT'
                }
                
                normalized_unit = unit_mapping.get(unit.upper(), unit)
                
                # Build product dictionary
                product = {
                    'name': name,
                    'price': price,
                    'unit': normalized_unit,
                    'quantity': quantity,
                    'supplierId': self.config.get('supplier_id', 0),  # Will be set by main.py
                    'brand': self.config.get('supplier_name', ''),    # Will be set by main.py
                    'description': name,
                    'image': image_url
                }
                
                products.append(product)
                
            except Exception as e:
                self.logger.error(f"Error extracting product: {e}")
                continue
        
        self.logger.info(f"Successfully extracted {len(products)} products from {url}")
        return products
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'strategy'):
            self.strategy.close()