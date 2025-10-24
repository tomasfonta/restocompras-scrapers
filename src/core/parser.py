"""Data parsing utilities for product information extraction."""

import re
from typing import Tuple, Dict, Any


class DataParser:
    """
    Utility class for parsing and cleaning product data.
    
    Provides standardized methods for extracting quantities, units,
    and prices from product text.
    """
    
    @staticmethod
    def parse_product_title(full_title: str) -> Tuple[str, str, str]:
        """
        Parse product title into name, quantity, and unit.
        
        Extracts quantity and unit from product titles like:
        - "Producto 500 gr"
        - "Producto 2 kilos"
        - "Producto 1 un."
        
        Standardizes units:
        - gr, un, u, lb → G
        - kilos, kg → KG
        - default → UNIT (quantity = 1)
        
        Args:
            full_title: Full product title string
            
        Returns:
            Tuple of (name, quantity, unit)
        """
        name = full_title.strip()
        
        # Remove leading 3-digit codes (e.g., "001 Producto")
        name = re.sub(r'^\s*\d{3}\s+', '', name).strip()
        
        # Match quantity and unit at end of string
        match = re.search(
            r'(\d+)\s*(gr|gramos?|kilos?|kg|un\.|u\.|lb)\.?$',
            name,
            re.IGNORECASE
        )
        
        quantity = "1"
        unit = "UNIT"
        
        if match:
            raw_quantity = match.group(1).strip()
            raw_unit = match.group(2).strip().lower().replace('.', '')
            
            # Standardize unit
            if raw_unit in ['gr', 'gramo', 'gramos', 'un', 'u', 'lb']:
                unit = "G"
            elif raw_unit in ['kilos', 'kilo', 'kg']:
                unit = "KG"
            else:
                unit = "UNIT"
            
            quantity = raw_quantity
            
            # Remove quantity and unit from name
            name = re.sub(
                r'\s*(\d+)\s*(gr|gramos?|kilos?|kg|un\.|u\.|lb)\.?$',
                '',
                name,
                flags=re.IGNORECASE
            ).strip()
        
        # Remove "por kilo" suffix
        name = re.sub(r'\s*por\s*kilo$', '', name, flags=re.IGNORECASE).strip()
        
        return name, quantity, unit
    
    @staticmethod
    def clean_price(price_text: str) -> Tuple[float, str]:
        """
        Clean and parse price text.
        
        Removes currency symbols and normalizes decimal separators.
        
        Args:
            price_text: Raw price text (e.g., "$1.234,56", "US$ 1234.56")
            
        Returns:
            Tuple of (numeric_price as float, formatted_price as string)
        """
        # Remove currency symbols and spaces
        cleaned = str(price_text).replace('$', '').replace('US$', '').strip()
        
        # Normalize decimal separators
        # Assume format: thousands separator = '.', decimal = ','
        # Or no separator and decimal = '.'
        cleaned = cleaned.replace('.', '').replace(',', '.')
        
        try:
            numeric_price = float(cleaned)
            # Return as int string for display (no decimals)
            formatted_price = str(int(numeric_price))
            return numeric_price, formatted_price
        except ValueError:
            return 0.0, price_text.strip()
    
    @staticmethod
    def standardize_product_data(raw_product: Dict[str, Any], supplier_id: int, 
                                 supplier_name: str) -> Dict[str, Any]:
        """
        Standardize raw product data into consistent format.
        
        Args:
            raw_product: Raw product dictionary from scraper
            supplier_id: Supplier ID to add
            supplier_name: Supplier name for brand field
            
        Returns:
            Standardized product dictionary
        """
        name = raw_product.get('name', 'N/A')
        price = raw_product.get('price', 0.0)
        
        standardized = {
            'name': name,
            'brand': raw_product.get('brand', supplier_name),
            'description': raw_product.get('description', name),
            'price': price,
            'image': raw_product.get('image', ''),
            'unit': raw_product.get('unit', 'UNIT'),
            'quantity': raw_product.get('quantity', '1'),
            'supplierId': supplier_id,
            'productId': None  # Will be filled by API lookup
        }
        
        return standardized
