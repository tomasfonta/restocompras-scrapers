"""Abstract base class for scraping strategies."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class ScrapingStrategy(ABC):
    """
    Abstract base class for different scraping strategies.
    
    Defines the interface for fetching HTML content from websites.
    Different strategies (Selenium, Requests, etc.) implement this interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize strategy with configuration.
        
        Args:
            config: Strategy-specific configuration
        """
        self.config = config
    
    @abstractmethod
    def fetch_html(self, url: str) -> str:
        """
        Fetch HTML content from the given URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string
            
        Raises:
            Exception: If fetching fails
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Clean up resources (browsers, connections, etc.).
        """
        pass
