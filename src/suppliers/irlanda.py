"""Irlanda supplier scraper for PDF price lists."""

import logging
from typing import List, Dict
import re

from ..core.scraper_base import ScraperBase
from ..strategies.pdf_strategy import PDFStrategy


class IrlandaScraper(ScraperBase):
    """
    Scraper for Irlanda supplier using PDF price lists.
    
    Extracts product data from PDF tables containing:
    - Product name
    - Price
    - Optional: Code, quantity, unit
    """
    
    def __init__(self, config: Dict, api_client):
        """
        Initialize Irlanda PDF scraper.
        
        Args:
            config: Configuration dictionary with PDF settings
            api_client: Backend API client for data integration
        """
        super().__init__(config, api_client)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # File configuration
        self.file_config = config.get('file_config', {})
        self.filename = self.file_config.get('filename')
        self.input_dir = self.file_config.get('input_dir', 'input')
        
        # PDF strategy
        pdf_config = config.get('pdf_config', {})
        pdf_config['input_dir'] = self.input_dir
        self.strategy = PDFStrategy(pdf_config)
        
        # Column mapping for flexible header detection
        self.column_mapping = config.get('column_mapping', {})
        
        # Price format
        self.price_format = config.get('price_format', {})
        
        self.logger.info(f"Irlanda PDF scraper initialized for file: {self.filename}")
    
    def get_urls(self) -> List[str]:
        """
        Return list of files to process.
        
        Returns:
            List with single filename
        """
        return [self.filename]
    
    def _fetch_html(self, filename: str) -> str:
        """
        Extract data from PDF file.
        
        Args:
            filename: Name of PDF file
            
        Returns:
            JSON string of extracted data
        """
        import json
        
        file_path = self.strategy.get_file_path(filename)
        raw_data = self.strategy.extract_data(file_path)
        
        self.logger.info(f"Extracted {len(raw_data)} raw records from PDF")
        
        return json.dumps(raw_data)
    
    def extract_products(self, json_content: str, filename: str) -> List[Dict]:
        """
        Process extracted PDF data into product format.
        
        Args:
            json_content: JSON string of raw extracted data
            filename: Source filename for logging
            
        Returns:
            List of product dictionaries
        """
        import json
        
        products = []
        
        try:
            raw_data = json.loads(json_content)
            
            self.logger.info(f"Processing {len(raw_data)} raw records")
            
            for row in raw_data:
                try:
                    product = self._extract_single_product(row)
                    if product:
                        products.append(product)
                except Exception as e:
                    self.logger.warning(f"Failed to process row: {e}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(products)} products from PDF")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error processing products: {e}", exc_info=True)
        
        return products
    
    def _extract_single_product(self, row: Dict) -> Dict:
        """
        Extract a single product from row data (text line or table row).
        
        Args:
            row: Dictionary with extracted row data
            
        Returns:
            Product dictionary or None if invalid
        """
        # Check if this is text mode (from line extraction)
        if 'text' in row:
            return self._extract_from_text_line(row['text'])
        
        # Table mode - Find name column
        name = self._find_column_value(row, self.column_mapping.get('name', []))
        if not name or name.strip() == '':
            return None
        
        # Find price column
        price_str = self._find_column_value(row, self.column_mapping.get('price', []))
        if not price_str:
            return None
        
        # Parse price
        price = self._parse_price(price_str)
        if price <= 0:
            return None
        
        # Find optional fields
        code = self._find_column_value(row, self.column_mapping.get('code', []))
        quantity_str = self._find_column_value(row, self.column_mapping.get('quantity', []))
        unit = self._find_column_value(row, self.column_mapping.get('unit', []))
        
        # Parse quantity
        quantity = 1
        if quantity_str:
            try:
                quantity = float(quantity_str.replace(',', '.'))
            except ValueError:
                pass
        
        # If no unit found, try to extract from name
        if not unit:
            parsed = self._parse_product_title(name)
            name = parsed.get('name', name)
            quantity = parsed.get('quantity', quantity)
            unit = parsed.get('unit', 'UNIT')
        else:
            unit = self._normalize_unit(unit)
        
        product = {
            'name': name.strip(),
            'brand': self.config['supplier_name'],
            'description': name.strip(),
            'price': price,
            'quantity': quantity,
            'unit': unit,
            'image': '',
            'code': code.strip() if code else '',
            'supplierId': self.config['supplier_id']
        }
        
        return product
    
    def _extract_from_text_line(self, line: str) -> Dict:
        """
        Extract product from text line format.
        
        Irlanda format: CODE DESCRIPTION............ PRICE
        Example: 0101137 SODA SIFON SOCIAL 2L.................. ... 5700.00
        
        Args:
            line: Text line from PDF
            
        Returns:
            Product dictionary or None if invalid
        """
        # Skip header lines
        if any(skip in line.lower() for skip in ['página', 'lista', 'código', 'descripción', '═══', '───', 'cuit:', 'direc:', 'tel:']):
            return None
        
        # Try to match pattern: CODE DESCRIPTION PRICE
        # Price is at the end, code at the beginning
        import re
        
        # Match price at end (numbers with optional dots for thousands and comma for decimals)
        # Pattern: 5700.00 or 3.700,00 or 12345,00
        price_match = re.search(r'[.\s]+(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+\.\d{2})\s*$', line)
        if not price_match:
            return None
        
        price_str = price_match.group(1)
        price = self._parse_price(price_str)
        if price <= 0:
            return None
        
        # Remove price from line
        line_without_price = line[:price_match.start()].strip()
        
        # Remove dots and "..." used as fillers
        line_without_price = re.sub(r'\.{2,}', ' ', line_without_price).strip()
        
        # Extract code (typically at start, 5-7 digits)
        code_match = re.match(r'^(\d{5,7})\s+', line_without_price)
        code = ''
        name = line_without_price
        
        if code_match:
            code = code_match.group(1)
            name = line_without_price[code_match.end():].strip()
        
        # Clean name
        name = re.sub(r'\s{2,}', ' ', name).strip()
        
        if not name:
            return None
        
        # Parse quantity and unit from name
        parsed = self._parse_product_title(name)
        
        product = {
            'name': parsed.get('name', name).strip(),
            'brand': self.config['supplier_name'],
            'description': parsed.get('name', name).strip(),
            'price': price,
            'quantity': parsed.get('quantity', 1),
            'unit': parsed.get('unit', 'UNIT'),
            'image': '',
            'code': code,
            'supplierId': self.config['supplier_id']
        }
        
        return product
    
    def _find_column_value(self, row: Dict, possible_names: List[str]) -> str:
        """
        Find value in row using multiple possible column names.
        
        Args:
            row: Row dictionary
            possible_names: List of possible column names to search
            
        Returns:
            Found value or empty string
        """
        for name in possible_names:
            if name in row and row[name]:
                return str(row[name]).strip()
        
        # Try partial matching
        row_keys = list(row.keys())
        for name in possible_names:
            for key in row_keys:
                if name in key.lower():
                    value = row[key]
                    if value and str(value).strip():
                        return str(value).strip()
        
        return ''
    
    def _parse_price(self, price_str: str) -> float:
        """
        Parse price string to float.
        
        Args:
            price_str: Price string
            
        Returns:
            Price as float
        """
        from ..core.parser import DataParser
        
        try:
            price, _ = DataParser.clean_price(price_str, self.price_format)
            return price
        except Exception:
            return 0.0
    
    def _parse_product_title(self, title: str) -> Dict:
        """
        Parse product title to extract quantity and unit.
        
        Args:
            title: Product title
            
        Returns:
            Dictionary with name, quantity, unit
        """
        from ..core.parser import DataParser
        
        name, quantity_str, unit = DataParser.parse_product_title(title)
        
        try:
            quantity = float(quantity_str)
        except ValueError:
            quantity = 1
        
        return {
            'name': name,
            'quantity': quantity,
            'unit': unit
        }
    
    def _normalize_unit(self, unit: str) -> str:
        """
        Normalize unit string.
        
        Args:
            unit: Raw unit string
            
        Returns:
            Normalized unit
        """
        unit = unit.upper().strip()
        
        unit_mapping = {
            'KG': 'KG',
            'KILO': 'KG',
            'KILOS': 'KG',
            'GR': 'G',
            'GRAMO': 'G',
            'GRAMOS': 'G',
            'L': 'L',
            'LITRO': 'L',
            'LITROS': 'L',
            'ML': 'ML',
            'CC': 'ML',
            'UN': 'UNIT',
            'UND': 'UNIT',
            'UNIDAD': 'UNIT'
        }
        
        return unit_mapping.get(unit, 'UNIT')
    
    def close(self):
        """Close the PDF strategy."""
        try:
            self.strategy.close()
            self.logger.info("Irlanda scraper closed")
        except Exception as e:
            self.logger.error(f"Error closing scraper: {e}")
