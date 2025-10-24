"""Requests-based scraping strategy for static websites."""

import requests
import logging
from typing import Dict, Any

from .scraping_strategy import ScrapingStrategy


class RequestsStrategy(ScrapingStrategy):
    """
    Scraping strategy using Python requests for static content.
    
    Use this strategy for websites that serve complete HTML content
    without requiring JavaScript execution.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Requests strategy.
        
        Args:
            config: Configuration dictionary with optional keys:
                - timeout: Request timeout in seconds (default: 15)
                - user_agent: Custom user agent string
                - headers: Additional HTTP headers
        """
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configuration with defaults
        self.timeout = config.get('timeout', 15)
        
        # Set up headers
        self.headers = {
            'User-Agent': config.get(
                'user_agent',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        }
        
        # Add any additional headers from config
        if 'headers' in config:
            self.headers.update(config['headers'])
        
        # Create session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        self.logger.info("Requests strategy initialized")
    
    def fetch_html(self, url: str) -> str:
        """
        Fetch HTML content using requests library.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string
            
        Raises:
            requests.exceptions.RequestException: If request fails
        """
        self.logger.info(f"Fetching URL with requests: {url}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()  # Raise exception for 4xx/5xx status codes
            
            # Get content with proper encoding
            html_content = response.text
            
            self.logger.info(
                f"Successfully fetched content from {url} "
                f"({len(html_content)} bytes, status: {response.status_code})"
            )
            
            return html_content
            
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Timeout fetching {url}: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error fetching {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error fetching {url}: {e}")
            raise
    
    def close(self) -> None:
        """Close the requests session and clean up resources."""
        try:
            self.session.close()
            self.logger.info("Requests session closed")
        except Exception as e:
            self.logger.error(f"Error closing requests session: {e}")
