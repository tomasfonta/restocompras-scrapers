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
                
                # Parse title to extract name, quantity, and unit
                name, quantity, unit = self.parser.parse_product_title(title)
                
                # Build product dictionary
                product = {
                    'name': name,
                    'brand': self.config.get('supplier_name', 'Distribuidora De Marchi'),
                    'description': title,
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
