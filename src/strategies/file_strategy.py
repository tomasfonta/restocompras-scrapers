"""Base strategy for file-based scraping (PDF, Excel, CSV, etc.)."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import os
import logging


class FileStrategy(ABC):
    """
    Abstract base class for file-based scraping strategies.
    
    Unlike web scraping strategies that fetch HTML from URLs,
    file strategies read local files (PDF, Excel, CSV, etc.) and
    extract structured data from them.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize file strategy with configuration.
        
        Args:
            config: Strategy-specific configuration including:
                - file_path: Path to the file to parse
                - input_dir: Base directory for input files
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.input_dir = config.get('input_dir', 'input')
    
    def get_file_path(self, filename: str) -> str:
        """
        Get full path to file in input directory.
        
        Args:
            filename: Name of file to locate
            
        Returns:
            Full path to file
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = os.path.join(self.input_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return file_path
    
    @abstractmethod
    def extract_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract structured data from file.
        
        Args:
            file_path: Path to file to parse
            
        Returns:
            List of dictionaries containing extracted data
            
        Raises:
            Exception: If extraction fails
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Clean up resources (file handles, temporary files, etc.).
        """
        pass
