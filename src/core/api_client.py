"""API client for backend communication."""

import requests
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote
import json


class APIClient:
    """
    Handles all communication with the backend API.
    
    Provides methods for product ID lookup and item posting with
    proper authentication and error handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize API client with configuration.
        
        Args:
            config: API configuration containing endpoints and auth token
        """
        self.base_url = config.get('base_url', 'http://localhost:8080')
        self.auth_token = config['auth_token']
        self.search_endpoint = config.get('search_endpoint', '/api/products/search/best-match')
        self.item_endpoint = config.get('item_endpoint', '/api/item')
        self.timeout = config.get('timeout', 10)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self._headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }
    
    def fetch_product_id(self, product_name: str) -> Optional[int]:
        """
        Fetch product ID using dual-strategy search.
        
        First tries full product name, then falls back to shortened name
        (first two words) if the initial search fails.
        
        Args:
            product_name: Name of the product to search for
            
        Returns:
            Product ID if found, None otherwise
        """
        # Strategy 1: Full product name
        product_id = self._search_product(product_name)
        if product_id is not None:
            return product_id
        
        # Strategy 2: Shortened name (first two words)
        words = product_name.split()
        if len(words) >= 2:
            short_name = " ".join(words[:2])
            self.logger.warning(
                f"First search failed for '{product_name}', "
                f"trying shortened name: '{short_name}'"
            )
            product_id = self._search_product(short_name)
            if product_id is not None:
                return product_id
        
        self.logger.warning(f"No product ID found for '{product_name}' (both strategies failed)")
        return None
    
    def _search_product(self, query: str) -> Optional[int]:
        """
        Perform actual API search request.
        
        Args:
            query: Search query string
            
        Returns:
            Product ID if found, None otherwise
        """
        search_url = f"{self.base_url}{self.search_endpoint}?query={quote(query)}"
        
        self.logger.info(f"Searching for product: {query}")
        self.logger.debug(f"GET {search_url}")
        
        try:
            response = requests.get(
                search_url,
                headers=self._headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check if response contains productId
            if isinstance(data, dict) and 'productId' in data and data['productId'] is not None:
                product_id = data['productId']
                self.logger.info(f"Found product ID {product_id} for '{query}'")
                return product_id
            
            self.logger.debug(f"No productId in response for '{query}': {data}")
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API search failed for '{query}': {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response for '{query}': {e}")
            return None
    
    def post_item(self, product_data: Dict[str, Any]) -> bool:
        """
        Post product item to the API.
        
        Args:
            product_data: Product data dictionary with all required fields
            
        Returns:
            True if successful, False otherwise
        """
        post_url = f"{self.base_url}{self.item_endpoint}"
        
        # Build payload from product data
        payload = {
            'name': product_data['name'],
            'description': product_data.get('description', product_data['name']),
            'price': product_data['price'],
            'image': product_data.get('image', ''),
            'productId': product_data['productId'],
            'unit': product_data['unit'],
            'quantity': product_data['quantity'],
            'supplierId': product_data['supplierId'],
            'brand': product_data['brand']
        }
        
        self.logger.debug(f"POST {post_url} - {product_data['name']}")
        
        try:
            response = requests.post(
                post_url,
                json=payload,
                headers=self._headers,
                timeout=self.timeout
            )
            
            # Log response details
            try:
                response_data = response.json()
                self.logger.debug(f"Response: {response_data}")
            except json.JSONDecodeError:
                self.logger.debug(f"Response text: {response.text[:200]}")
            
            response.raise_for_status()
            
            self.logger.info(
                f"Successfully posted {product_data['name']} "
                f"(ID: {product_data['productId']}) - Status: {response.status_code}"
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API post failed for {product_data['name']}: {e}")
            
            # Try to log error response
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    self.logger.error(f"Error response: {error_data}")
                except:
                    self.logger.error(f"Error response text: {e.response.text[:200]}")
            
            return False
    
    def update_auth_token(self, new_token: str) -> None:
        """
        Update the authentication token.
        
        Args:
            new_token: New JWT token
        """
        self.auth_token = new_token
        self._headers['Authorization'] = f'Bearer {new_token}'
        self.logger.info("Auth token updated")
