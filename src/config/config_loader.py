"""Configuration loading and management."""

import json
import os
import logging
from typing import Dict, Any, Optional


class ConfigLoader:
    """
    Loads and manages configuration from JSON files.
    
    Handles loading of both API configuration and supplier-specific configs.
    """
    
    def __init__(self, config_dir: str = 'configs'):
        """
        Initialize config loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)
    
    def load_api_config(self, config_file: str = 'api_config.json') -> Dict[str, Any]:
        """
        Load API configuration.
        
        Args:
            config_file: Name of API config file
            
        Returns:
            API configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        filepath = os.path.join(self.config_dir, config_file)
        
        self.logger.info(f"Loading API config from {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ['auth_token']
        missing = [field for field in required_fields if field not in config]
        
        if missing:
            raise ValueError(f"API config missing required fields: {missing}")
        
        self.logger.info("API config loaded successfully")
        return config
    
    def load_supplier_config(self, supplier_name: str) -> Dict[str, Any]:
        """
        Load supplier-specific configuration.
        
        Args:
            supplier_name: Name of supplier (e.g., 'greenshop', 'lacteos_granero')
            
        Returns:
            Supplier configuration dictionary
            
        Raises:
            FileNotFoundError: If supplier config doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        # Look in configs/suppliers/ directory
        suppliers_dir = os.path.join(self.config_dir, 'suppliers')
        filepath = os.path.join(suppliers_dir, f'{supplier_name}.json')
        
        self.logger.info(f"Loading supplier config from {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ['supplier_id', 'supplier_name', 'scraping_strategy']
        missing = [field for field in required_fields if field not in config]
        
        if missing:
            raise ValueError(f"Supplier config missing required fields: {missing}")
        
        self.logger.info(f"Supplier config loaded for {config['supplier_name']}")
        return config
    
    def list_suppliers(self) -> list:
        """
        List all available supplier configurations.
        
        Returns:
            List of supplier names (without .json extension)
        """
        suppliers_dir = os.path.join(self.config_dir, 'suppliers')
        
        if not os.path.exists(suppliers_dir):
            return []
        
        suppliers = []
        for filename in os.listdir(suppliers_dir):
            if filename.endswith('.json'):
                supplier_name = filename[:-5]  # Remove .json extension
                suppliers.append(supplier_name)
        
        return sorted(suppliers)
    
    def save_supplier_config(self, supplier_name: str, config: Dict[str, Any]) -> None:
        """
        Save supplier configuration to file.
        
        Args:
            supplier_name: Name of supplier
            config: Configuration dictionary to save
        """
        suppliers_dir = os.path.join(self.config_dir, 'suppliers')
        os.makedirs(suppliers_dir, exist_ok=True)
        
        filepath = os.path.join(suppliers_dir, f'{supplier_name}.json')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved supplier config to {filepath}")
