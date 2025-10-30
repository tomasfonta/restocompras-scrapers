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
        self.base_url = config.get('base_url', 'https://restocompras2.onrender.com')
        self.auth_token = config.get('auth_token', '')
        self.login_endpoint = config.get('login_endpoint', '/login')
        self.search_endpoint = config.get('search_endpoint', '/api/products/search/best-match')
        self.item_endpoint = config.get('item_endpoint', '/api/item')
        self.supplier_search_endpoint = config.get('supplier_search_endpoint', '/api/suppliers/search')
        self.timeout = config.get('timeout', 10)
        self.credentials = config.get('credentials', {})
        # Use the main logger instance instead of creating a separate one
        self.logger = logging.getLogger('restocompras_scraper')
        
        self._headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }
    
    def login(self) -> Optional[str]:
        """
        Authenticate with the backend API and retrieve JWT token.
        
        Uses credentials from config to login and extracts the authentication
        token from the response headers if successful (status code 200).
        
        Returns:
            JWT token string if login successful, None otherwise
        """
        if not self.credentials or not self.credentials.get('name') or not self.credentials.get('password'):
            self.logger.error("Login credentials not provided in config")
            return None
        
        return self.login_with_credentials(
            self.credentials['name'],
            self.credentials['password']
        )
    
    def login_with_credentials(self, name: str, password: str) -> Optional[str]:
        """
        Authenticate with the backend API using provided credentials.
        
        Args:
            name: User email
            password: User password
            
        Returns:
            JWT token string if login successful, None otherwise
        """
        login_url = f"{self.base_url}{self.login_endpoint}"
        
        payload = {
            'name': name,
            'password': password
        }
        
        self.logger.info(f"Attempting login for user: {name}")
        
        # 📤 REQUEST LOGGING
        self.logger.info(f"📤 POST {login_url}")
        self.logger.debug(f"📤 Request headers: {{'Content-Type': 'application/json'}}")
        self.logger.debug(f"📤 Request body: {payload}")
        
        try:
            response = requests.post(
                login_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            # 📥 RESPONSE LOGGING
            self.logger.info(f"📥 Response status: {response.status_code}")
            self.logger.debug(f"📥 Response headers: {json.dumps(dict(response.headers), indent=2)}")
            
            # Log response body (sanitized for security)
            try:
                response_body = response.json()
                # Create sanitized version for logging
                sanitized_body = {}
                if isinstance(response_body, dict):
                    for key, value in response_body.items():
                        if any(token_key in key.lower() for token_key in ['token', 'jwt', 'auth', 'password']):
                            sanitized_body[key] = "***REDACTED***"
                        else:
                            sanitized_body[key] = value
                    self.logger.debug(f"📥 Response body: {json.dumps(sanitized_body, indent=2)}")
                else:
                    self.logger.debug(f"📥 Response body type: {type(response_body).__name__}")
            except json.JSONDecodeError:
                self.logger.debug(f"📥 Response body (text): {response.text[:200]}")
            except Exception as e:
                self.logger.debug(f"📥 Response body parsing error: {e}")
            
            if response.status_code == 200:
                # Extract token from response headers
                # Common header names: 'Authorization', 'authentication', 'x-auth-token', etc.
                token = None
                
                # Try different common header names
                for header_name in ['Authorization', 'authorization', 'Authentication', 'authentication', 
                                   'x-auth-token', 'X-Auth-Token', 'token', 'Token']:
                    if header_name in response.headers:
                        token = response.headers[header_name]
                        # Remove 'Bearer ' prefix if present
                        if token.startswith('Bearer '):
                            token = token[7:]
                        self.logger.info(f"Token found in header '{header_name}'")
                        break
                
                # If not in headers, check response body
                if not token:
                    try:
                        data = response.json()
                        # Try common JSON keys for token
                        for key in ['token', 'access_token', 'accessToken', 'jwt', 'authToken']:
                            if key in data:
                                token = data[key]
                                self.logger.info(f"Token found in response body key '{key}'")
                                break
                    except json.JSONDecodeError:
                        self.logger.warning("Could not parse response body as JSON")
                
                if token:
                    self.logger.info("✅ Login successful, token retrieved")
                    # Update the client's auth token and headers
                    self.auth_token = token
                    self._headers['Authorization'] = f'Bearer {token}'
                    return token
                else:
                    self.logger.warning("⚠️ Login returned 200 but no token found in headers or body")
                    self.logger.debug(f"📥 Available response headers: {list(response.headers.keys())}")
                    try:
                        response_data = response.json()
                        available_keys = list(response_data.keys()) if isinstance(response_data, dict) else []
                        self.logger.debug(f"📥 Available response body keys: {available_keys}")
                    except:
                        self.logger.debug(f"📥 Response body preview: {response.text[:500]}")
                    return None
            else:
                self.logger.error(f"❌ Login failed with status code: {response.status_code}")
                try:
                    error_data = response.json()
                    self.logger.error(f"📥 Error response body: {json.dumps(error_data, indent=2)}")
                except:
                    self.logger.error(f"📥 Error response text: {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"🔌 Login request failed: {e}")
            return None
    
    def fetch_supplier_details(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Fetch supplier details from the backend API.
        
        Called after successful login to retrieve supplier information
        such as supplier ID, name, and other metadata from the backend.
        
        Args:
            email: Supplier email address to search for
            
        Returns:
            Dictionary with supplier details if found, None otherwise
        """
        search_url = f"{self.base_url}{self.supplier_search_endpoint}?email={(email)}"
        
        self.logger.info(f"Fetching supplier details for: {email}")
        
        # 📤 REQUEST LOGGING
        self.logger.info(f"📤 GET {search_url}")
        self.logger.debug(f"📤 Request headers: {json.dumps({k: '***' if 'authorization' in k.lower() else v for k, v in self._headers.items()}, indent=2)}")
        
        try:
            response = requests.get(
                search_url,
                headers=self._headers,
                timeout=self.timeout
            )
            
            # 📥 RESPONSE LOGGING
            self.logger.info(f"📥 Response status: {response.status_code}")
            self.logger.debug(f"📥 Response headers: {json.dumps(dict(response.headers), indent=2)}")
            
            if response.status_code == 200:
                supplier_data = response.json()
                self.logger.debug(f"📥 Response body: {json.dumps(supplier_data, indent=2)}")
                
                # Log supplier info with enhanced details
                if isinstance(supplier_data, dict):
                    supplier_id = supplier_data.get('id') or supplier_data.get('supplierId')
                    supplier_name = supplier_data.get('name') or supplier_data.get('supplierName')
                    supplier_email = supplier_data.get('email', 'N/A')
                    supplier_status = supplier_data.get('status', 'N/A')
                    
                    if supplier_id:
                        self.logger.info(f"✅ Supplier found - ID: {supplier_id}, Name: {supplier_name or 'N/A'}")
                        self.logger.debug(f"📊 Supplier details - Email: {supplier_email}, Status: {supplier_status}")
                    else:
                        self.logger.warning(f"⚠️ Supplier data retrieved but no ID found")
                        self.logger.debug(f"📥 Available keys: {list(supplier_data.keys())}")
                    
                    return supplier_data
                elif isinstance(supplier_data, list) and len(supplier_data) > 0:
                    # If response is a list, take the first supplier
                    supplier = supplier_data[0]
                    supplier_id = supplier.get('id') or supplier.get('supplierId')
                    supplier_name = supplier.get('name') or supplier.get('supplierName')
                    self.logger.info(f"✅ Supplier found (array response) - ID: {supplier_id}, Name: {supplier_name or 'N/A'}")
                    self.logger.debug(f"📊 Response contains {len(supplier_data)} suppliers, using first one")
                    return supplier
                else:
                    self.logger.warning(f"⚠️ Unexpected supplier data format: {type(supplier_data).__name__}")
                    self.logger.debug(f"📥 Raw response: {json.dumps(supplier_data, indent=2)}")
                    return supplier_data
            elif response.status_code == 404:
                self.logger.warning(f"❌ Supplier not found for email: {email}")
                try:
                    error_body = response.json()
                    self.logger.debug(f"📥 404 Response body: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.debug(f"📥 404 Response text: {response.text}")
                return None
            else:
                self.logger.error(f"❌ Failed to fetch supplier details - Status: {response.status_code}")
                try:
                    error_data = response.json()
                    self.logger.error(f"📥 Error response body: {json.dumps(error_data, indent=2)}")
                except:
                    self.logger.error(f"📥 Error response text: {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"🔌 Supplier details request failed for '{email}': {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"📥 Invalid JSON response for supplier '{email}': {e}")
            self.logger.debug(f"📥 Raw response text: {response.text[:500]}")
            return None
    
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
        
        # 📤 REQUEST LOGGING
        self.logger.info(f"🔍 Searching for product: '{query}'")
        self.logger.info(f"📤 GET {search_url}")
        self.logger.debug(f"📤 Request headers: {json.dumps({k: '***' if 'authorization' in k.lower() else v for k, v in self._headers.items()}, indent=2)}")
        self.logger.debug(f"📤 Query parameters: {{'query': query}}")
        
        try:
            response = requests.get(
                search_url,
                headers=self._headers,
                timeout=self.timeout
            )
            
            # 📥 RESPONSE LOGGING
            self.logger.info(f"📥 Response status: {response.status_code}")
            self.logger.debug(f"📥 Response headers: {json.dumps(dict(response.headers), indent=2)}")
            
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"📥 Response body: {json.dumps(data, indent=2)}")
            
            # Check if response contains productId
            if isinstance(data, dict) and 'productId' in data and data['productId'] is not None:
                
                product_id = data['productId']
                product_name = data.get('name', 'N/A')
                product_category = data.get('category', 'N/A')
                self.logger.info(f"✅ Found product ID {product_id} for '{query}'")
                self.logger.debug(f"📊 Product details - Name: {product_name}, Category: {product_category}")
                return product_id
            
            self.logger.warning(f"⚠️ No productId in response for '{query}'")
            if isinstance(data, dict):
                available_keys = list(data.keys())
                self.logger.debug(f"📥 Available response keys: {available_keys}")
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ API search failed for '{query}': {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.debug(f"📥 Error response status: {e.response.status_code}")
                try:
                    error_body = e.response.json()
                    self.logger.debug(f"📥 Error response body: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.debug(f"📥 Error response text: {e.response.text[:200]}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"📥 Invalid JSON response for '{query}': {e}")
            self.logger.debug(f"📥 Raw response text: {response.text[:200]}")
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
        
        # 📤 REQUEST LOGGING
        self.logger.info(f"📦 Posting product: '{product_data['name']}'")
        self.logger.info(f"📤 POST {post_url}")
        self.logger.debug(f"📤 Request headers: {json.dumps({k: '***' if 'authorization' in k.lower() else v for k, v in self._headers.items()}, indent=2)}")
        self.logger.debug(f"📤 Request body: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                post_url,
                json=payload,
                headers=self._headers,
                timeout=self.timeout
            )
            
            # 📥 RESPONSE LOGGING
            self.logger.info(f"📥 Response status: {response.status_code}")
            self.logger.debug(f"📥 Response headers: {json.dumps(dict(response.headers), indent=2)}")
            
            # Log response details
            try:
                response_data = response.json()
                self.logger.debug(f"📥 Response body: {json.dumps(response_data, indent=2)}")
                
                # Extract useful information from response
                if isinstance(response_data, dict):
                    item_id = response_data.get('id') or response_data.get('itemId')
                    created_at = response_data.get('createdAt') or response_data.get('created_at')
                    if item_id:
                        self.logger.debug(f"📊 Created item ID: {item_id}")
                    if created_at:
                        self.logger.debug(f"📊 Created at: {created_at}")
                        
            except json.JSONDecodeError:
                self.logger.debug(f"📥 Response body (text): {response.text[:200]}")
            
            response.raise_for_status()
            
            self.logger.info(
                f"✅ Successfully posted '{product_data['name']}' "
                f"(Product ID: {product_data['productId']}, Supplier ID: {product_data['supplierId']})"
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ API post failed for '{product_data['name']}': {e}")
            
            # Try to log error response with enhanced details
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"📥 Error response status: {e.response.status_code}")
                self.logger.debug(f"📥 Error response headers: {json.dumps(dict(e.response.headers), indent=2)}")
                try:
                    error_data = e.response.json()
                    self.logger.error(f"📥 Error response body: {json.dumps(error_data, indent=2)}")
                    
                    # Extract specific error information
                    if isinstance(error_data, dict):
                        error_message = error_data.get('message') or error_data.get('error')
                        error_code = error_data.get('code') or error_data.get('errorCode')
                        if error_message:
                            self.logger.error(f"💬 Error message: {error_message}")
                        if error_code:
                            self.logger.error(f"🔢 Error code: {error_code}")
                            
                except:
                    self.logger.error(f"📥 Error response text: {e.response.text[:200]}")
            
            return False
    
    def update_auth_token(self, new_token: str) -> None:
        """
        Update the authentication token.
        
        Args:
            new_token: New JWT token
        """
        self.auth_token = new_token
        self._headers['Authorization'] = f'Bearer {new_token}'
        self.logger.info("🔑 Auth token updated successfully")
