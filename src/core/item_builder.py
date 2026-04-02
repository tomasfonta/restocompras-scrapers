"""ItemBuilder module for transforming scraped products into API items.

This module provides configuration-driven transformation of raw scraped products
into ItemCreateRequestDto format with supplier-specific customizations.
All item creation logic is here, allowing adjustments without modifying the API.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
import re


class ItemBuilder:
    """
    Transforms scraped product data into ItemCreateRequestDto format.
    
    Supports supplier-specific transformations via configuration:
    - Field mapping and aliasing
    - Price adjustments (markup, fixed adjustments, rounding rules)
    - Unit conversions
    - Field validation and defaults
    - Custom transformation functions
    """
    
    def __init__(self, supplier_config: Dict[str, Any]):
        """
        Initialize ItemBuilder with supplier configuration.
        
        Args:
            supplier_config: Supplier-specific configuration dictionary
                           including optional 'item_transform' section
        """
        self.supplier_config = supplier_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Extract item transformation configuration
        self.transform_config = supplier_config.get('item_transform', {})
        self.supplier_id = supplier_config.get('supplier_id')
        self.supplier_name = supplier_config.get('supplier_name')
        
        # Load transformation rules
        self._load_transform_rules()
    
    def _load_transform_rules(self) -> None:
        """Load and validate transformation rules from configuration."""
        self.field_mappings = self.transform_config.get('field_mappings', {})
        self.price_adjustments = self.transform_config.get('price_adjustments', {})
        self.unit_mappings = self.transform_config.get('unit_mappings', {})
        self.validations = self.transform_config.get('validations', {})
        self.defaults = self.transform_config.get('defaults', {})
    
    def build_item(self, product_data: Dict[str, Any], product_id: int) -> Optional[Dict[str, Any]]:
        """
        Transform scraped product into ItemCreateRequestDto.
        
        Args:
            product_data: Raw scraped product data
            product_id: Product ID from backend catalog
            
        Returns:
            ItemCreateRequestDto format or None if validation fails
        """
        try:
            item = {}
            
            # Apply field mappings
            item['name'] = self._map_field(product_data, 'name', product_data.get('name', 'Unknown'))
            item['description'] = self._map_field(product_data, 'description', product_data.get('description', item['name']))
            item['brand'] = self._map_field(product_data, 'brand', self.supplier_name)
            item['image'] = self._map_field(product_data, 'image', product_data.get('image', ''))
            
            # Price processing with adjustments
            raw_price = product_data.get('price', 0)
            item['price'] = self._apply_price_adjustments(raw_price)
            
            # Unit and quantity processing
            item['unit'] = self._map_unit(product_data.get('unit', 'U'))
            qty = self._map_field(product_data, 'quantity', product_data.get('quantity', 1))
            # Ensure quantity is numeric
            item['quantity'] = self._parse_quantity_value(qty)
            
            # Required fields
            item['productId'] = product_id
            item['supplierId'] = self.supplier_id
            
            # Optional fields from product data or defaults
            item['providerItemId'] = product_data.get('providerItemId')
            
            # Log transformation
            self.logger.debug(
                f"Built item: {item['name']} - "
                f"Price: {item['price']}, Unit: {item['unit']}, Qty: {item['quantity']}"
            )
            
            return item
            
        except Exception as e:
            self.logger.error(f"Error building item from product {product_data.get('name')}: {e}", exc_info=True)
            return None
    
    def _map_field(self, product_data: Dict[str, Any], field_name: str, default: Any) -> Any:
        """
        Map a field using configured mappings or return default.
        
        Args:
            product_data: Raw product data
            field_name: Field to map (e.g., 'name', 'brand')
            default: Default value if not found
            
        Returns:
            Mapped value or default
        """
        # Check if there's a custom mapping rule (e.g., "name" -> "product_title")
        mapping = self.field_mappings.get(field_name)
        
        if mapping:
            if isinstance(mapping, str):
                # Simple field alias: use this key from product_data
                return product_data.get(mapping, default)
            elif isinstance(mapping, dict):
                # Complex mapping with transformation function
                source_field = mapping.get('source')
                transform = mapping.get('transform')
                value = product_data.get(source_field, default)
                
                if transform and value != default:
                    return self._apply_transform(transform, value)
                return value
        
        return default
    
    def _apply_transform(self, transform_name: str, value: Any) -> Any:
        """
        Apply a named transformation function.
        
        Args:
            transform_name: Name of transformation (e.g., 'uppercase', 'trim', 'parse_quantity')
            value: Value to transform
            
        Returns:
            Transformed value
        """
        if transform_name == 'uppercase':
            return str(value).upper()
        elif transform_name == 'lowercase':
            return str(value).lower()
        elif transform_name == 'trim':
            return str(value).strip()
        elif transform_name == 'remove_special_chars':
            return re.sub(r'[^\w\s]', '', str(value))
        elif transform_name == 'parse_quantity':
            return self._parse_quantity_value(value)
        else:
            self.logger.warning(f"Unknown transform: {transform_name}")
            return value
    
    def _parse_quantity_value(self, value: Any) -> float:
        """Parse quantity value, extracting numeric part if needed."""
        if isinstance(value, (int, float)):
            return float(value)
        
        text = str(value).strip().lower()
        # Extract first number found
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            return float(match.group(1))
        return 1.0
    
    def _apply_price_adjustments(self, raw_price: float) -> float:
        """
        Apply supplier-specific price adjustments.
        
        Supported adjustments:
        - 'markup_percent': Add percentage markup
        - 'fixed_adjustment': Add/subtract fixed amount
        - 'rounding': Round to nearest X (e.g., 0.50)
        - 'min_price': Ensure price >= min
        - 'max_price': Ensure price <= max
        
        Args:
            raw_price: Raw price from scraper
            
        Returns:
            Adjusted price
        """
        price = Decimal(str(raw_price))
        
        # Apply markup percentage
        if 'markup_percent' in self.price_adjustments:
            markup = Decimal(str(self.price_adjustments['markup_percent']))
            price = price * (1 + markup / 100)
        
        # Apply fixed adjustment
        if 'fixed_adjustment' in self.price_adjustments:
            adjustment = Decimal(str(self.price_adjustments['fixed_adjustment']))
            price = price + adjustment
        
        # Round to nearest value
        if 'rounding' in self.price_adjustments:
            rounding = Decimal(str(self.price_adjustments['rounding']))
            if rounding > 0:
                price = (price / rounding).quantize(0) * rounding
        
        # Apply min/max bounds
        if 'min_price' in self.price_adjustments:
            min_price = Decimal(str(self.price_adjustments['min_price']))
            price = max(price, min_price)
        
        if 'max_price' in self.price_adjustments:
            max_price = Decimal(str(self.price_adjustments['max_price']))
            price = min(price, max_price)
        
        # Ensure price is not negative
        price = max(price, Decimal('0'))
        
        return float(price)
    
    def _map_unit(self, raw_unit: str) -> str:
        """
        Map scraped unit to standard unit enum.
        
        Standard units: KG, LT, U (unidad), DOC (docena), etc.
        
        Args:
            raw_unit: Raw unit from scraper
            
        Returns:
            Mapped standard unit
        """
        raw_unit = str(raw_unit).strip().upper()
        
        # Check custom mappings first
        if raw_unit in self.unit_mappings:
            return self.unit_mappings[raw_unit]
        
        # Default mappings for common variations
        # API accepts: G, KG, ML, L, UNIT
        default_mappings = {
            'KG': 'KG',
            'KILOGRAMO': 'KG',
            'KILOGRAMOS': 'KG',
            'K': 'KG',
            'L': 'L',
            'LT': 'L',
            'LITRO': 'L',
            'LITROS': 'L',
            'U': 'UNIT',
            'UN': 'UNIT',
            'UNIDAD': 'UNIT',
            'UNIDADES': 'UNIT',
            'DOC': 'UNIT',
            'DOCENA': 'UNIT',
            'PACK': 'UNIT',
            'BOX': 'UNIT',
            'BOTELLA': 'UNIT',
            'LATA': 'UNIT',
            'ML': 'ML',
            'GR': 'G',
            'G': 'G',
            'GRAMO': 'G',
            'GRAMOS': 'G',
        }
        
        return default_mappings.get(raw_unit, 'UNIT')
    
    def _validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validate item meets all requirements.
        
        Args:
            item: Item to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        required_fields = ['name', 'price', 'productId', 'supplierId', 'unit']
        for field in required_fields:
            if field not in item or not item[field]:
                self.logger.warning(f"Item missing required field: {field}")
                return False
        
        # Validate price is positive
        if item['price'] <= 0:
            self.logger.warning(f"Item '{item['name']}' has invalid price: {item['price']}")
            return False
        
        # Check custom validation rules
        if 'price_range' in self.validations:
            price_range = self.validations['price_range']
            if 'min' in price_range and item['price'] < price_range['min']:
                self.logger.warning(
                    f"Item '{item['name']}' price {item['price']} below minimum {price_range['min']}"
                )
                return False
            if 'max' in price_range and item['price'] > price_range['max']:
                self.logger.warning(
                    f"Item '{item['name']}' price {item['price']} above maximum {price_range['max']}"
                )
                return False
        
        # Validate name length
        if len(item['name']) < 3:
            self.logger.warning(f"Item name too short: {item['name']}")
            return False
        
        if len(item['name']) > 255:
            self.logger.warning(f"Item name too long: {item['name'][:50]}...")
            item['name'] = item['name'][:255]
        
        return True
    
    def build_batch(self, products: List[Dict[str, Any]], product_ids_map: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Build multiple items from products using product ID lookup map.
        
        Args:
            products: List of raw scraped products
            product_ids_map: Mapping of product_name -> product_id
            
        Returns:
            List of valid ItemCreateRequestDto objects
        """
        items = []
        
        for product in products:
            product_name = product.get('name')
            if not product_name:
                self.logger.warning("Product has no name, skipping")
                continue
            
            product_id = product_ids_map.get(product_name)
            if not product_id:
                self.logger.warning(f"No product ID for '{product_name}'")
                continue
            
            item = self.build_item(product, product_id)
            if item:
                items.append(item)
        
        self.logger.info(f"Built {len(items)} valid items from {len(products)} products")
        return items
