"""Utility modules."""

from .text_processing import deduplicate_products, normalize_text, extract_numeric_value
from .logger import setup_logger

__all__ = ['deduplicate_products', 'normalize_text', 'extract_numeric_value', 'setup_logger']
