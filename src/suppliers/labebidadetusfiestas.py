"""La Bebida de Tus Fiestas scraper implementation."""

from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

from ..core.scraper_base import ScraperBase
from ..core.parser import DataParser
from ..strategies import RequestsStrategy


class LaBebidaDeTusFiestasScraper(ScraperBase):
    """
    Scraper for La Bebida de Tus Fiestas website using requests strategy.
    
    This supplier uses PrestaShop and includes unit information in the title.
    Important: CC (cubic centimeters) must be mapped to ML (milliliters)
    - Example: "1500CC" → quantity=1500, unit=ML
    - Example: "187CC" → quantity=187, unit=ML
    """
    
    def __init__(self, config: Dict[str, Any], api_client: 'APIClient'):
        """
        Initialize La Bebida de Tus Fiestas scraper.
        
        Args:
            config: Supplier configuration
            api_client: API client instance
        """
        super().__init__(config, api_client)
        
        # Initialize scraping strategy
        strategy_config = config.get('strategy_config', {})
        self.strategy = RequestsStrategy(strategy_config)
        
        # Get selectors from config
        self.selectors = config.get('selectors', {})
        
        # Initialize parser
        self.parser = DataParser()
        
        # Base URL for resolving relative paths
        self.base_url = 'https://labebidadetusfiestas.com.ar'
    
    def get_urls(self) -> List[str]:
        """Get list of URLs to scrape from configuration."""
        return self.config.get('urls', [])
    
    def _fetch_html(self, url: str) -> str:
        """
        Fetch HTML content using requests strategy.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string
        """
        return self.strategy.fetch_html(url)
    
    def _parse_unit_from_title(self, title: str) -> Tuple[str, str, str]:
        """
        Parse unit from title with special CC → ML conversion.
        
        This supplier uses CC (cubic centimeters) in titles, which must be
        converted to ML (milliliters). 1 CC = 1 ML.
        
        Patterns:
        - '1500CC' → quantity=1500, unit=ML
        - '187CC' → quantity=187, unit=ML
        - '750ML' → quantity=750, unit=ML
        - '1L' or '1 LITRO' → quantity=1, unit=L
        
        Args:
            title: Product title string
            
        Returns:
            Tuple of (cleaned_name, quantity, unit)
        """
        name = title.strip()
        quantity = "1"
        unit = "UNIT"
        
        # Pattern 1: 'CC' (cubic centimeters) → ML
        # Examples: "1500CC", "187CC", "750CC"
        match = re.search(r'(\d+)\s*CC\b', name, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            unit = "ML"  # CC = ML (1:1 conversion)
            # Remove the matched part from name
            name = name[:match.start()] + name[match.end():]
            name = re.sub(r'\s+', ' ', name).strip()
            return (name, quantity, unit)
        
        # Pattern 2: 'ML' (milliliters)
        match = re.search(r'(\d+)\s*ML\b', name, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            unit = "ML"
            name = name[:match.start()] + name[match.end():]
            name = re.sub(r'\s+', ' ', name).strip()
            return (name, quantity, unit)
        
        # Pattern 3: 'L' or 'LITRO' or 'LITROS' (liters)
        match = re.search(r'(\d+\.?\d*)\s*(L|LITROS?)\b', name, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            unit = "L"
            name = name[:match.start()] + name[match.end():]
            name = re.sub(r'\s+', ' ', name).strip()
            return (name, quantity, unit)
        
        # Clean up extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        return (name, quantity, unit)
    
    def extract_products(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        """
        Extract product data from HTML content.
        
        Args:
            html_content: Raw HTML string
            url: Source URL (for logging purposes)
            
        Returns:
            List of product dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        # Find all product items using PrestaShop class
        product_selector = self.selectors.get('product_list', '.product-miniature')
        product_items = soup.select(product_selector)
        
        self.logger.info(f"Found {len(product_items)} product items on page")
        
        for item in product_items:
            try:
                # Extract title
                title_selector = self.selectors.get('title', '.product-title a')
                title_element = item.select_one(title_selector)
                
                # Extract price
                price_selector = self.selectors.get('price', '.product-price')
                price_element = item.select_one(price_selector)
                
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
                
                # Parse price using configured format
                price_format = self.config.get('price_format', {})
                price, formatted_price = self.parser.clean_price(price_text, price_format)
                
                # Extract image URL
                image_selector = self.selectors.get('image', 'img')
                image_element = item.select_one(image_selector)
                image_url = ''
                
                if image_element:
                    # PrestaShop uses lazy loading with data-src
                    image_url = (
                        image_element.get('data-src', '') or
                        image_element.get('src', '')
                    )
                    
                    # Ensure absolute URL
                    if image_url and not image_url.startswith('http'):
                        if image_url.startswith('//'):
                            image_url = 'https:' + image_url
                        elif image_url.startswith('/'):
                            image_url = urljoin(self.base_url, image_url)
                
                # Parse title to extract name, quantity, and unit with CC→ML conversion
                name, quantity, unit = self._parse_unit_from_title(title)
                
                # Build product dictionary
                product = {
                    'name': name,
                    'brand': self.config.get('supplier_name', 'La Bebida de Tus Fiestas'),
                    'description': title,  # Keep original title as description
                    'price': price,
                    'quantity': quantity,
                    'unit': unit,
                    'image': image_url,
                    'supplierId': self.config.get('supplier_id', 0),
                }
                
                products.append(product)
                
            except Exception as e:
                self.logger.warning(f"Failed to extract product: {e}")
                continue
        
        self.logger.info(
            f"Successfully extracted {len(products)} products from page"
        )
        
        return products
