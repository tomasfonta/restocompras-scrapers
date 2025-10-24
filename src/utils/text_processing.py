"""Utility functions for text processing and data manipulation."""

from typing import List, Dict, Any, Tuple


def deduplicate_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate products based on (name, unit, quantity) tuple.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        List of unique products
    """
    unique_products = {}
    
    for product in products:
        # Create unique key from name, unit, and quantity
        unique_key = (
            product.get('name', ''),
            product.get('unit', 'UNIT'),
            product.get('quantity', '1')
        )
        
        # Keep first occurrence
        if unique_key not in unique_products:
            unique_products[unique_key] = product
    
    return list(unique_products.values())


def normalize_text(text: str) -> str:
    """
    Normalize text by removing extra whitespace and special characters.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    normalized = ' '.join(text.split())
    
    return normalized.strip()


def extract_numeric_value(text: str) -> float:
    """
    Extract first numeric value from text.
    
    Args:
        text: Text containing numeric value
        
    Returns:
        Extracted numeric value or 0.0 if not found
    """
    import re
    
    # Find first numeric pattern (supports decimals)
    match = re.search(r'\d+(?:[.,]\d+)?', text)
    
    if match:
        # Normalize decimal separator
        value_str = match.group().replace(',', '.')
        try:
            return float(value_str)
        except ValueError:
            return 0.0
    
    return 0.0
