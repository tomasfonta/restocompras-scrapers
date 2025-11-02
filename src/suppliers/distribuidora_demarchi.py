"""Distribuidora De Marchi scraper implementation."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

from ..core.scraper_base import ScraperBase
from ..core.parser import DataParser
from ..strategies import RequestsStrategy


class DistribuidoraDeMarchiScraper(ScraperBase):
    """
    Scraper for Distribuidora De Marchi website using requests strategy.
    
    This supplier uses the Tiendanube e-commerce platform with static HTML.
    Only products with the "agregar al carrito" button have prices and should be scraped.
    """
    
    def __init__(self, config: Dict[str, Any], api_client: 'APIClient'):
        """
        Initialize Distribuidora De Marchi scraper.
        
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
        self.base_url = 'https://www.distribuidorademarchi.com.ar'
    
    def _parse_demarchi_title(self, title: str) -> tuple:
        """
        Parse De Marchi product title to extract name, brand, and full title for units.
        
        De Marchi format: "Product Name Brand x 500 g – Description"
        - Product name: Everything before the last word before 'x'
        - Brand: Last word before 'x'
        - Full title: Used for parsing units and quantity
        
        Examples:
            "Aderezo Caesar Abedul x 20 g – Pack x108 unidades"
            -> name: "Aderezo Caesar", brand: "Abedul"
            
            "Aderezo Caesar Abedul x20 g – Pack x108 unidades"
            -> name: "Aderezo Caesar", brand: "Abedul"
            
            "Aderezo Caesar Abedul x – Pack x108 unidades"
            -> name: "Aderezo Caesar", brand: "Abedul"
            
            "Chipa Congelado x 5 kg – Formato mayorista"
            -> name: "Chipa", brand: "Congelado", units from "x 5 kg"
        
        Args:
            title: Raw product title
            
        Returns:
            Tuple of (product_name, brand, full_title)
        """
        # Find the FIRST position of 'x' followed by:
        # - a digit (with or without space): " x20", " x 20"
        # - or a dash/separator: " x –", " x -"
        # This ensures we match the x that indicates quantity, not other x's in the text
        x_match = re.search(r'\s+x\s*(?=\d|[–-])', title, re.IGNORECASE)
        
        if x_match:
            # Get everything before ' x'
            before_x = title[:x_match.start()].strip()
            
            # Split by spaces to separate product name and brand
            words = before_x.split()
            
            if len(words) >= 2:
                # Last word before 'x' is the brand
                brand = words[-1]
                # Everything else is the product name
                product_name = ' '.join(words[:-1])
            elif len(words) == 1:
                # Only one word, use it as product name, brand is supplier name
                product_name = words[0]
                brand = self.config.get('supplier_name', 'Distribuidora De Marchi')
            else:
                # Empty before x, use full title
                product_name = title
                brand = self.config.get('supplier_name', 'Distribuidora De Marchi')
        else:
            # No 'x' found, use full title as product name
            product_name = title
            brand = self.config.get('supplier_name', 'Distribuidora De Marchi')
        
        return product_name, brand, title
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
    
    def extract_products(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        """
        Extract product data from HTML content.
        
        Only extracts products that have the "agregar al carrito" button,
        as these are the products with prices available.
        
        Args:
            html_content: Raw HTML string
            url: Source URL (for logging purposes)
            
        Returns:
            List of product dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        # Find all product items using Tiendanube class
        product_selector = self.selectors.get('product_list', '.js-item-product')
        product_items = soup.select(product_selector)
        
        self.logger.info(f"Found {len(product_items)} product items on page")
        
        for item in product_items:
            try:
                # IMPORTANT: Only process products with "agregar al carrito" button
                button_selector = self.selectors.get('button', '.js-addtocart')
                button = item.select_one(button_selector)
                
                if not button:
                    # Skip products without the "agregar al carrito" button (no price)
                    continue
                
                # Extract title
                title_selector = self.selectors.get('title', '.js-item-name')
                title_element = item.select_one(title_selector)
                
                # Extract price
                price_selector = self.selectors.get('price', '.js-price-display')
                price_element = item.select_one(price_selector)
                
                # Extract image
                image_selector = self.selectors.get('image', '.js-item-image')
                image_element = item.select_one(image_selector)
                
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
                image_url = ''
                if image_element:
                    # Tiendanube uses lazy loading with data-srcset
                    image_url = (
                        image_element.get('data-srcset', '') or
                        image_element.get('data-src', '') or
                        image_element.get('src', '')
                    )
                    
                    # data-srcset might have multiple URLs with sizes, take the first one
                    if image_url and ' ' in image_url:
                        image_url = image_url.split()[0]
                    
                    # Ensure absolute URL
                    if image_url and not image_url.startswith('http'):
                        # Add https: if it starts with //
                        if image_url.startswith('//'):
                            image_url = 'https:' + image_url
                        else:
                            image_url = urljoin(self.base_url, image_url)
                
                # Parse De Marchi title to extract product name and brand
                product_name, brand, full_title = self._parse_demarchi_title(title)
                
                # Parse the full title to extract quantity and unit
                # The parser will use the full title (with "x N unit") to get units
                _, quantity, unit = self.parser.parse_product_title(full_title)
                
                self.logger.debug(f"Parsed '{title}' -> Name: '{product_name}', Brand: '{brand}', {quantity} {unit}")
                
                # Build product dictionary
                product = {
                    'name': product_name,  # Use parsed product name (without brand)
                    'brand': brand,  # Use extracted brand
                    'description': title,  # Keep full title as description
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
            f"Successfully extracted {len(products)} products with prices from page"
        )
        
        return products
