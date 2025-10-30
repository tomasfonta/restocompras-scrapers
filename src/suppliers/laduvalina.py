"""La Duvalina scraper implementation."""

from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

from ..core.scraper_base import ScraperBase
from ..core.parser import DataParser
from ..strategies import SeleniumStrategy


class LaduvalinaScraper(ScraperBase):
    """
    Scraper for La Duvalina website using Selenium strategy.
    
    This supplier uses WooCommerce with specific unit patterns in titles:
    - '10kg' or '10k' means 10 kilograms
    - 'x100 un' means 100 units
    - 'x unidad' means 1 unit
    - '1 kilo' means 1 kilogram
    
    Some products may not have images (use placeholder).
    Uses Selenium due to site loading requirements.
    """
    
    def __init__(self, config: Dict[str, Any], api_client: 'APIClient'):
        """
        Initialize La Duvalina scraper.
        
        Args:
            config: Supplier configuration
            api_client: API client instance
        """
        super().__init__(config, api_client)
        
        # Initialize scraping strategy - using Selenium for reliability
        strategy_config = config.get('strategy_config', {})
        self.strategy = SeleniumStrategy(strategy_config)
        
        # Get selectors from config
        self.selectors = config.get('selectors', {})
        
        # Initialize parser
        self.parser = DataParser()
        
        # Base URL for resolving relative paths
        self.base_url = 'https://laduvalina.com.ar'
        
        # Placeholder image for products without images
        self.placeholder_image = 'https://via.placeholder.com/300x300.png?text=No+Image'
    
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
        Parse La Duvalina-specific unit patterns from product title.
        
        Patterns:
        - '10kg' or '10k' → quantity=10, unit=KG
        - 'x100 un' → quantity=100, unit=UNIT
        - 'x unidad' → quantity=1, unit=UNIT
        - '1 kilo' or '1kg' → quantity=1, unit=KG
        - '500g' or '500 gr' → quantity=500, unit=G
        
        Args:
            title: Product title string
            
        Returns:
            Tuple of (cleaned_name, quantity, unit)
        """
        name = title.strip()
        quantity = "1"
        unit = "UNIT"
        
        # Pattern 1: 'x 10kg' or '10kg' or '10k' (kilograms)
        match = re.search(r'[x\s]?(\d+\.?\d*)\s*(kg|k|kilos?)\b', name, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            unit = "KG"
            # Remove the matched part from name
            name = name[:match.start()] + name[match.end():]
            name = name.strip()
            return (name, quantity, unit)
        
        # Pattern 2: 'x100 un' or 'x 100 un' (units)
        match = re.search(r'[x\s](\d+)\s*un\b', name, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            unit = "UNIT"
            name = name[:match.start()] + name[match.end():]
            name = name.strip()
            return (name, quantity, unit)
        
        # Pattern 3: 'x unidad' (single unit)
        match = re.search(r'[x\s]unidad\b', name, re.IGNORECASE)
        if match:
            quantity = "1"
            unit = "UNIT"
            name = name[:match.start()] + name[match.end():]
            name = name.strip()
            return (name, quantity, unit)
        
        # Pattern 4: '500g' or '500 gr' or '500 gramos' (grams)
        match = re.search(r'(\d+\.?\d*)\s*(g|gr|gramos?)\b', name, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            unit = "G"
            name = name[:match.start()] + name[match.end():]
            name = name.strip()
            return (name, quantity, unit)
        
        # Pattern 5: '500ml' or '1 litro' (liters/ml)
        match = re.search(r'(\d+\.?\d*)\s*(ml|litros?|l)\b', name, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            raw_unit = match.group(2).lower()
            unit = "L" if raw_unit in ['litro', 'litros', 'l'] else "ML"
            name = name[:match.start()] + name[match.end():]
            name = name.strip()
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
        
        # Find all product items using WooCommerce class
        product_selector = self.selectors.get('product_list', '.product')
        product_items = soup.select(product_selector)
        
        self.logger.info(f"Found {len(product_items)} product items on page")
        
        for item in product_items:
            try:
                # Extract title
                title_selector = self.selectors.get('title', '.woocommerce-loop-product__title')
                title_element = item.select_one(title_selector)
                
                # Extract price - get the last price amount (after discounts)
                price_selector = self.selectors.get('price', '.price')
                price_container = item.select_one(price_selector)
                
                # Validate required fields
                if not title_element or not price_container:
                    self.logger.warning("Missing title or price, skipping product")
                    continue
                
                # Get text content
                title = title_element.get_text(strip=True)
                
                # Skip empty titles
                if not title:
                    continue
                
                # Extract final price (last amount element)
                price_amounts = price_container.select('.woocommerce-Price-amount')
                if price_amounts:
                    price_text = price_amounts[-1].get_text(strip=True)
                else:
                    price_text = price_container.get_text(strip=True)
                
                # Parse price using configured format
                price_format = self.config.get('price_format', {})
                price, formatted_price = self.parser.clean_price(price_text, price_format)
                
                # Extract image URL
                image_selector = self.selectors.get('image', 'img')
                image_element = item.select_one(image_selector)
                image_url = self.placeholder_image  # Default to placeholder
                
                if image_element:
                    # Try different image source attributes
                    image_url = (
                        image_element.get('src', '') or
                        image_element.get('data-src', '') or
                        image_element.get('data-lazy-src', '')
                    )
                    
                    # Check if it's a real image or placeholder
                    if not image_url or 'placeholder' in image_url.lower():
                        image_url = self.placeholder_image
                    elif image_url and not image_url.startswith('http'):
                        # Ensure absolute URL
                        image_url = urljoin(self.base_url, image_url)
                
                # Parse title to extract name, quantity, and unit using custom logic
                name, quantity, unit = self._parse_unit_from_title(title)
                
                # Build product dictionary
                product = {
                    'name': name,
                    'brand': self.config.get('supplier_name', 'La Duvalina'),
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
