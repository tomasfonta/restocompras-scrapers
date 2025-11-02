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
        
        # Extract description (additional text that may contain weight/unit info)
        description_selector = self.selectors.get('description', '.product__details__top__description')
        description_tag = item.select_one(description_selector)
        description_text = description_tag.text.strip() if description_tag else ""
        
        # Try to extract unit info from description if present
        # Example: "El precio por kilo es $804 y el monto final depende del peso de cada horma (4kg aprox.)."
        name, quantity, unit = self._parse_product_info(full_title, description_text)
        
        # Extract price
        price_selector = self.selectors.get('price', '.product__details__price--legacy__current--legacy')
        price_tag = item.select_one(price_selector)
        price_text = price_tag.text.strip() if price_tag else "$0"
        
        # Clean and convert price using custom format from config
        price_format = self.config.get('price_format', {})
        price, _ = self.parser.clean_price(price_text, price_format)
        
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
    
    def _parse_product_info(self, title: str, description: str) -> tuple:
        """
        Parse product information from title and description.
        
        Tries to extract unit information from:
        1. The title first (e.g., "Queso 500g")
        2. Special cases: "por kilo" → 1 KG, "por horma" → check description
        3. The description if title doesn't contain units (e.g., "(4kg aprox.)")
        
        Args:
            title: Product title
            description: Additional product description text
            
        Returns:
            Tuple of (name, quantity, unit)
        """
        import re
        
        # First try parsing the title
        name, quantity, unit = self.parser.parse_product_title(title)
        
        # Special case: "por kilo" in title means 1 KG
        if "por kilo" in title.lower():
            if unit == "UNIT":  # Only if no other unit was detected
                unit = "KG"
                quantity = "1"
                # Remove "por kilo" from name
                name = re.sub(r'\s*por\s+kilo\s*', '', name, flags=re.IGNORECASE).strip()
                self.logger.debug(f"Detected 'por kilo' in title: {name} → 1 KG")
        
        # Special case: "por horma" in title - check description for weight
        if "por horma" in title.lower() and description:
            # Look for weight in description
            match = re.search(
                r'[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*(kg|kilo|kilos|g|gr|gramos?)\s*(?:aprox\.?|aproximadamente)?[\)\]]?',
                description,
                re.IGNORECASE
            )
            
            if match:
                raw_quantity = match.group(1).strip().replace(',', '.')
                raw_unit = match.group(2).strip().lower()
                
                # Standardize unit
                if raw_unit in ['g', 'gr', 'gramo', 'gramos']:
                    unit = "G"
                elif raw_unit in ['kg', 'kilo', 'kilos']:
                    unit = "KG"
                
                # Convert quantity
                try:
                    quantity_float = float(raw_quantity)
                    if quantity_float.is_integer():
                        quantity = str(int(quantity_float))
                    else:
                        quantity = str(quantity_float)
                except ValueError:
                    quantity = raw_quantity
                
                self.logger.debug(f"Detected 'por horma' with weight in description: {name} → {quantity} {unit}")
        
        # If no unit was found in title (defaults to UNIT), check description
        elif unit == "UNIT" and description:
            # Look for patterns like "(4kg aprox.)", "4 kg aprox", "500g aprox.", etc.
            # Match: (number + optional decimal + unit + optional "aprox")
            match = re.search(
                r'[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*(kg|kilo|kilos|g|gr|gramos?|l|litros?|cc|ml)\s*(?:aprox\.?|aproximadamente)?[\)\]]?',
                description,
                re.IGNORECASE
            )
            
            if match:
                raw_quantity = match.group(1).strip().replace(',', '.')
                raw_unit = match.group(2).strip().lower()
                
                # Standardize unit (same logic as parser)
                if raw_unit in ['g', 'gr', 'gramo', 'gramos']:
                    unit = "G"
                elif raw_unit in ['kg', 'kilo', 'kilos']:
                    unit = "KG"
                elif raw_unit in ['l', 'litro', 'litros']:
                    unit = "L"
                elif raw_unit in ['cc', 'ml']:
                    unit = "ML"
                
                # Convert quantity to string, handling decimals
                try:
                    quantity_float = float(raw_quantity)
                    if quantity_float.is_integer():
                        quantity = str(int(quantity_float))
                    else:
                        quantity = str(quantity_float)
                except ValueError:
                    quantity = raw_quantity
                
                self.logger.debug(f"Extracted unit from description: {quantity} {unit} (from: {description[:50]}...)")
        
        return name, quantity, unit
    
    def __del__(self):
        """Clean up strategy resources."""
        if hasattr(self, 'strategy'):
            self.strategy.close()
