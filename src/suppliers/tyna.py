"""TYNA supplier scraper using direct API requests."""

import requests
import logging
import json
from typing import List, Dict
from urllib.parse import urlencode

from ..core.scraper_base import ScraperBase
from ..core.parser import DataParser


class TYNAScraper(ScraperBase):
    """
    Scraper for TYNA supplier using their API endpoint.
    
    TYNA uses a POST API endpoint that returns JSON data directly,
    making it more efficient than HTML scraping.
    """
    
    def __init__(self, config: Dict, api_client):
        """
        Initialize TYNA scraper.
        
        Args:
            config: Configuration dictionary with API settings
            api_client: Backend API client for data integration
        """
        super().__init__(config, api_client)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # API configuration
        self.api_config = config.get('api_config', {})
        self.base_url = self.api_config.get('base_url')
        self.headers = self.api_config.get('headers', {})
        self.timeout = self.api_config.get('timeout', 20)
        
        # Pagination settings
        pagination = self.api_config.get('pagination', {})
        self.start_param = pagination.get('start_param', 'start')
        self.limit_param = pagination.get('limit_param', 'limit')
        self.limit_value = pagination.get('limit_value', 100)
        self.initial_start = pagination.get('initial_start', 0)
        
        # Subcategories to scrape
        self.subcategories = config.get('subcategories', [])
        
        # Data mapping for extracting fields from response
        self.data_mapping = config.get('data_mapping', {})
        
        # Initialize parser
        self.parser = DataParser()
        
        # Create session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        self.logger.info(f"TYNA scraper initialized with {len(self.subcategories)} subcategories")
    
    def get_urls(self) -> List[str]:
        """
        Generate API request configurations for each subcategory.
        
        Returns:
            List of subcategory identifiers (used for API requests)
        """
        # Return subcategory IDs as "URLs" (we'll use them for API requests)
        return [subcat['id'] for subcat in self.subcategories]
    
    def _fetch_html(self, subcategory_id: str) -> str:
        """
        Fetch data from API for a specific subcategory.
        
        Args:
            subcategory_id: The subcategory ID to fetch
            
        Returns:
            JSON response as string
        """
        # Find subcategory config
        subcategory = next(
            (s for s in self.subcategories if s['id'] == subcategory_id),
            None
        )
        
        if not subcategory:
            self.logger.error(f"Subcategory {subcategory_id} not found in config")
            return "[]"
        
        category = subcategory.get('category', '003')
        subcategory_name = subcategory.get('name', subcategory_id)
        
        self.logger.info(f"Fetching products for subcategory: {subcategory_name} ({subcategory_id})")
        
        try:
            # Build request parameters
            params = f"{self.start_param}={self.initial_start}&{self.limit_param}={self.limit_value}&order=1"
            
            # Build form data
            form_data = {
                'orden': '1',
                'title': '',
                'categories[]': category,
                'subcategories[]': subcategory_id
            }
            
            # Make POST request
            response = self.session.post(
                f"{self.base_url}?{params}",
                data=form_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            json_data = response.json()
            products_count = len(json_data.get('products', []))
            
            self.logger.info(
                f"Successfully fetched {products_count} products "
                f"from subcategory {subcategory_name}"
            )
            
            return json.dumps(json_data)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error for subcategory {subcategory_id}: {e}")
            return "[]"
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error for subcategory {subcategory_id}: {e}")
            return "[]"
    
    def extract_products(self, json_content: str, subcategory_id: str) -> List[Dict]:
        """
        Extract product data from API JSON response.
        
        Args:
            json_content: JSON response as string
            subcategory_id: The subcategory ID being processed
            
        Returns:
            List of product dictionaries
        """
        products = []
        
        try:
            data = json.loads(json_content)
            raw_products = data.get('products', [])
            
            self.logger.info(f"Extracting data from {len(raw_products)} products")
            
            for item in raw_products:
                try:
                    product = self._extract_single_product(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    self.logger.warning(f"Failed to extract product: {e}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(products)} products from subcategory {subcategory_id}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error extracting products: {e}", exc_info=True)
        
        return products
    
    def _extract_single_product(self, item: Dict) -> Dict:
        """
        Extract a single product from API response item.
        
        Args:
            item: Product item from API response
            
        Returns:
            Product dictionary with standardized fields
        """
        data = item.get('data', {})
        images = item.get('images', [])
        
        # Extract title
        title = data.get('titulo', '').strip()
        if not title:
            return None
        
        # Extract price (precio_final is the final price)
        price_str = data.get('precio_final', data.get('precio', '0'))
        price_format = self.config.get('price_format', {})
        try:
            # Use clean_price for consistent price parsing
            price, _ = self.parser.clean_price(str(price_str), price_format)
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid price for product {title}: {price_str}")
            price = 0.0
        
        # Extract image URL
        image_url = ''
        if images and len(images) > 0:
            image_url = images[0].get('url', '')
        
        # Extract other fields
        code = data.get('cod_producto', '')
        stock = data.get('stock', '0')
        
        # Parse title to extract quantity and unit
        # TYNA titles follow pattern: "BRAND NAME *QUANTITY UNIT"
        # Example: "CAÑUELAS ACEITE GIRASOL COMUN *1.5 LTS"
        parsed_data = self._parse_product_title(title)
        
        product = {
            'name': parsed_data.get('name', title),
            'brand': self.config.get('supplier_name', 'TYNA'),
            'description': parsed_data.get('name', title),
            'price': price,
            'quantity': parsed_data.get('quantity', 1),
            'unit': parsed_data.get('unit', 'UNIT'),
            'image': image_url,
            'supplierId': self.config.get('supplier_id', 0),
            'code': code,
            'stock': stock
        }
        
        return product
    
    def _parse_product_title(self, title: str) -> Dict:
        """
        Parse TYNA product title to extract name, quantity, and unit.
        
        TYNA format: "BRAND PRODUCT NAME *QUANTITY UNIT"
        Example: "CAÑUELAS ACEITE GIRASOL COMUN *1.5 LTS"
        
        Args:
            title: Product title string
            
        Returns:
            Dictionary with name, quantity, unit
        """
        result = {
            'name': title,
            'quantity': 1,
            'unit': 'UNIT'
        }
        
        # Split by asterisk
        if '*' in title:
            parts = title.split('*')
            name_part = parts[0].strip()
            
            if len(parts) > 1:
                quantity_part = parts[1].strip()
                
                # Extract quantity and unit
                # Common patterns: "1.5 LTS", "500 ML", "900 CC", "150 GR"
                tokens = quantity_part.split()
                
                if len(tokens) >= 1:
                    # Try to extract numeric quantity
                    try:
                        quantity = float(tokens[0].replace(',', '.'))
                        result['quantity'] = quantity
                        
                        # Extract unit if present
                        if len(tokens) >= 2:
                            unit = tokens[1].upper()

                            unit = unit.replace('.', '')
                            
                            # Normalize units
                            unit_mapping = {
                                'LTS': 'L',
                                'LT': 'L',
                                'LITRO': 'L',
                                'L': 'L',
                                'LITROS': 'L',
                                'ML': 'ML',
                                'ML.': 'ML',
                                'CC': 'ML',
                                'CC.': 'ML',
                                'GR': 'G',
                                'GR.': 'G',
                                'GRAMOS': 'G',
                                'KG': 'KG',
                                'K': 'KG',
                                'KG.': 'KG',
                                'KILOS': 'KG',
                                'UN': 'UNIT',
                                'UN.': 'UNIT',
                                'U': 'UNIT',
                            }
                            
                            result['unit'] = unit_mapping.get(unit, unit)
                    except (ValueError, IndexError):
                        pass
                
                result['name'] = name_part
        
        return result
    
    def close(self):
        """Close the requests session."""
        try:
            self.session.close()
            self.logger.info("TYNA session closed")
        except Exception as e:
            self.logger.error(f"Error closing session: {e}")
