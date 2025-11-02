"""El Chañar Carnes scraper for Excel price lists."""

import logging
from typing import List, Dict
import json

from ..core.scraper_base import ScraperBase
from ..strategies.excel_strategy import ExcelStrategy


class ElChanarCarnesScraper(ScraperBase):
    """
    Scraper for El Chañar Carnes using Excel price lists.
    
    Supports multiple column layouts:
    - Single column: Name | Price
    - Paired columns: Name1 | Price1 | Name2 | Price2
    - Multi-sheet workbooks
    """
    
    def __init__(self, config: Dict, api_client):
        """
        Initialize Excel scraper.
        
        Args:
            config: Configuration dictionary with Excel settings
            api_client: Backend API client for data integration
        """
        super().__init__(config, api_client)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # File configuration
        self.file_config = config.get('file_config', {})
        self.filename = self.file_config.get('filename')
        self.input_dir = self.file_config.get('input_dir', 'input')
        
        # Excel strategy
        excel_config = config.get('excel_config', {})
        excel_config['input_dir'] = self.input_dir
        self.strategy = ExcelStrategy(excel_config)
        
        # Column mapping
        self.column_mapping = config.get('column_mapping', {})
        self.name_columns = self.column_mapping.get('name_columns', [0])
        self.price_columns = self.column_mapping.get('price_columns', [1])
        self.process_mode = self.column_mapping.get('process_mode', 'single')
        
        # Price format
        self.price_format = config.get('price_format', {})
        
        self.logger.info(f"Excel scraper initialized for file: {self.filename}")
    
    def get_urls(self) -> List[str]:
        """
        Return list of files to process.
        
        Returns:
            List with single filename
        """
        return [self.filename]
    
    def _fetch_html(self, filename: str) -> str:
        """
        Extract data from Excel file.
        
        Args:
            filename: Name of Excel file
            
        Returns:
            JSON string of extracted data
        """
        file_path = self.strategy.get_file_path(filename)
        raw_data = self.strategy.extract_data(file_path)
        
        self.logger.info(f"Extracted {len(raw_data)} raw records from Excel")
        
        return json.dumps(raw_data)
    
    def extract_products(self, json_content: str, filename: str) -> List[Dict]:
        """
        Process extracted Excel data into product format.
        
        Args:
            json_content: JSON string of raw extracted data
            filename: Source filename for logging
            
        Returns:
            List of product dictionaries
        """
        products = []
        
        try:
            raw_data = json.loads(json_content)
            
            self.logger.info(f"Processing {len(raw_data)} raw records in {self.process_mode} mode")
            
            if self.process_mode == 'paired':
                products = self._extract_paired_columns(raw_data)
            else:
                products = self._extract_single_columns(raw_data)
            
            self.logger.info(f"Successfully extracted {len(products)} products from Excel")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error processing products: {e}", exc_info=True)
        
        return products
    
    def _extract_single_columns(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Extract products from single name/price column layout.
        
        Args:
            raw_data: List of row dictionaries
            
        Returns:
            List of product dictionaries
        """
        products = []
        
        for row in raw_data:
            try:
                # Get column values by index
                name = self._get_column_by_index(row, self.name_columns[0])
                price_str = self._get_column_by_index(row, self.price_columns[0])
                
                product = self._create_product(name, price_str)
                if product:
                    products.append(product)
            except Exception as e:
                self.logger.debug(f"Skipping row: {e}")
                continue
        
        return products
    
    def _extract_paired_columns(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Extract products from paired column layout (Name1|Price1|Name2|Price2).
        
        Args:
            raw_data: List of row dictionaries
            
        Returns:
            List of product dictionaries
        """
        products = []
        
        for row in raw_data:
            # Process each name/price pair
            for name_col, price_col in zip(self.name_columns, self.price_columns):
                try:
                    name = self._get_column_by_index(row, name_col)
                    price_str = self._get_column_by_index(row, price_col)
                    
                    product = self._create_product(name, price_str)
                    if product:
                        products.append(product)
                except Exception as e:
                    self.logger.debug(f"Skipping column pair: {e}")
                    continue
        
        return products
    
    def _get_column_by_index(self, row: Dict, col_index: int) -> str:
        """
        Get column value by index.
        
        Args:
            row: Row dictionary
            col_index: Column index
            
        Returns:
            Column value as string
        """
        # Try to get by numeric key
        if col_index in row:
            return str(row[col_index]).strip()
        
        # Try to get by string key
        str_key = str(col_index)
        if str_key in row:
            return str(row[str_key]).strip()
        
        # Try to get from ordered keys
        keys = sorted([k for k in row.keys() if isinstance(k, (int, str)) and str(k).isdigit()])
        if col_index < len(keys):
            key = keys[col_index]
            return str(row[key]).strip()
        
        return ''
    
    def _create_product(self, name: str, price_str: str) -> Dict:
        """
        Create product dictionary from name and price.
        
        Args:
            name: Product name
            price_str: Price string
            
        Returns:
            Product dictionary or None if invalid
        """
        # Validate name
        if not name or name.strip() == '' or name.lower() == 'nan':
            return None
        
        # Validate price
        if not price_str or price_str.strip() == '' or price_str.lower() == 'nan':
            return None
        
        # Parse price
        price = self._parse_price(price_str)
        if price <= 0:
            return None
        
        # Parse title for quantity and unit
        parsed = self._parse_product_title(name)
        
        product = {
            'name': parsed.get('name', name).strip(),
            'brand': self.config['supplier_name'],
            'description': parsed.get('name', name).strip(),
            'price': price,
            'quantity': parsed.get('quantity', 1),
            'unit': parsed.get('unit', 'UNIT'),
            'image': '',
            'code': '',
            'supplierId': self.config['supplier_id']
        }
        
        return product
    
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
    
    def close(self):
        """Close the Excel strategy."""
        try:
            self.strategy.close()
            self.logger.info("Excel scraper closed")
        except Exception as e:
            self.logger.error(f"Error closing scraper: {e}")
