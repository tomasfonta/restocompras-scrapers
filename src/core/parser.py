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
    def parse_product_title(full_title: str, default_unit: str = 'UNIT') -> Tuple[str, str, str]:
        """
        Parse product title into name, quantity, and unit.
        
        Extracts quantity and unit from product titles like:
        - "Producto 500 gr", "Producto 500g", "Producto 500 gramos"
        - "Producto 2 kilos", "Producto 2kg", "Producto 2 kg"
        - "Producto 1 litro", "Producto 1l", "Producto 1 L"
        - "Producto 500cc", "Producto 500 cc", "Producto 500ml"
        - "Producto x 1 kg", "Producto x 500g"
        - "Chipa x 5 kg – Formato mayorista"
        - "Producto 1 un.", "Producto 1u"
        
        Standardizes units:
        - gr, g, gramos, un, u, lb → G
        - kilos, kilo, kg → KG
        - litros, litro, l → L
        - cc, ml, mililitros → ML
        - default → UNIT (quantity = 1)
        
        Args:
            full_title: Full product title string
            
        Returns:
            Tuple of (name, quantity, unit)
        """
        name = full_title.strip()
        
        # Remove leading 3-digit codes (e.g., "001 Producto")
        name = re.sub(r'^\s*\d{3}\s+', '', name).strip()
        
        # Try to match quantity and unit patterns
        # First attempt: at the end of string (most common)
        # Second attempt: followed by dash/hyphen (e.g., "x 5 kg – description")
        
        # Pattern with various formats:
        # - "500 gr", "500gr", "500 g", "500g"
        # - "x 500 gr", "x 500g" (with optional "x" prefix)
        # - "1 litro", "1l", "1 L"
        # - "500cc", "500 cc", "500ml", "500 ml"
        unit_pattern = r'(?:x\s+)?(\d+(?:[.,]\d+)?)\s*(gr|g|gramos?|kilos?|kilo|kg|litros?|l|cc|ml|mililitros?|un\.|u\.|u|lb)\.?'
        
        # Try at end of string first
        match = re.search(unit_pattern + r'$', name, re.IGNORECASE)
        
        # If not found at end, try before dash/hyphen (common in De Marchi format)
        if not match:
            match = re.search(unit_pattern + r'\s*[–-]', name, re.IGNORECASE)
        
        # If still not found, try anywhere in the string (but prefer first occurrence)
        if not match:
            match = re.search(unit_pattern, name, re.IGNORECASE)
        
        quantity = "1"
        unit = default_unit
        matched_text = ""
        
        if match:
            raw_quantity = match.group(1).strip().replace(',', '.')
            raw_unit = match.group(2).strip().lower().replace('.', '')
            
            # Get the full matched text, but strip any trailing dash that might be included
            # (when matching before a dash, the pattern includes the dash)
            matched_text = match.group(0).rstrip('–-').strip()
            
            # Standardize unit
            if raw_unit in ['gr', 'g', 'gramo', 'gramos', 'un', 'u', 'lb']:
                unit = "G"
            elif raw_unit in ['kilos', 'kilo', 'kg']:
                unit = "KG"
            elif raw_unit in ['litros', 'litro', 'l']:
                unit = "L"
            elif raw_unit in ['cc', 'ml', 'mililitro', 'mililitros']:
                unit = "ML"
            else:
                unit = "UNIT"
            
            # Convert quantity to integer if it's a whole number
            try:
                quantity_float = float(raw_quantity)
                if quantity_float.is_integer():
                    quantity = str(int(quantity_float))
                else:
                    quantity = str(quantity_float)
            except ValueError:
                quantity = raw_quantity
            
            # Remove the matched unit pattern from name
            # Check if the matched text is followed by a dash (De Marchi format: "x N unit – description")
            pattern_with_dash = re.escape(matched_text) + r'\s*[–-]'
            if re.search(pattern_with_dash, name):
                # Replace "x N unit" before dash, keeping the dash
                name = re.sub(pattern_with_dash, ' –', name)
            else:
                # Standard removal for end-of-string matches or other positions
                name = name.replace(matched_text, '')
            
            # Normalize only separator dashes (those with spaces), not hyphens in compound words
            # Only normalize dashes that have at least one space on either side
            name = re.sub(r'\s+[–-]\s*', ' – ', name)  # Space before dash
            name = re.sub(r'\s*[–-]\s+', ' – ', name)  # Space after dash
            name = re.sub(r'\s+', ' ', name)  # Normalize multiple spaces
            name = name.strip()
        
        # Remove "por kilo" suffix
        name = re.sub(r'\s*por\s*kilo$', '', name, flags=re.IGNORECASE).strip()
        
        return name, quantity, unit
    
    @staticmethod
    def clean_price(price_text: str, price_format: Dict[str, str] = None) -> Tuple[float, str]:
        """
        Clean and parse price text with custom format support.
        
        Removes currency symbols and normalizes decimal separators based on
        the provided price format configuration.
        
        Args:
            price_text: Raw price text (e.g., "$1.234,56", "1.400", "1400,00")
            price_format: Optional dict with 'thousands_separator' and 'decimal_separator' keys
                         If None, uses default format (thousands='.', decimal=',')
            
        Returns:
            Tuple of (numeric_price as float, formatted_price as string)
            
        Examples:
            # Default format (thousands='.', decimal=',')
            clean_price("$1.234,56") -> (1234.56, "1234.56")
            
            # Green Shop format (thousands='.', no decimal)
            clean_price("1.400", {"thousands_separator": ".", "decimal_separator": ""}) -> (1400.0, "1400.00")
            
            # Piala format (thousands='.', decimal=',')
            clean_price("1.400,00", {"thousands_separator": ".", "decimal_separator": ","}) -> (1400.0, "1400.00")
        """
        # Remove currency symbols and extra spaces
        cleaned = str(price_text).replace('$', '').replace('US$', '').replace('AR$', '').strip()
        
        # Get format configuration or use defaults
        if price_format is None:
            price_format = {}
        
        thousands_sep = price_format.get('thousands_separator', '.')
        decimal_sep = price_format.get('decimal_separator', ',')
        
        # Remove thousands separator
        if thousands_sep:
            cleaned = cleaned.replace(thousands_sep, '')
        
        # Replace decimal separator with standard '.'
        if decimal_sep and decimal_sep != '.':
            cleaned = cleaned.replace(decimal_sep, '.')
        
        try:
            numeric_price = float(cleaned)
            # Format with 2 decimal places
            formatted_price = f"{numeric_price:.2f}"
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
