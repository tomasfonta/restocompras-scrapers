"""Data export utilities for saving scraped data."""

import pandas as pd
import logging
import os
from typing import List, Dict, Any
from datetime import datetime


class DataExporter:
    """
    Handles exporting scraped data to various formats.
    
    Currently supports Excel export with standardized column structure.
    """
    
    def __init__(self, output_dir: str = 'output'):
        """
        Initialize exporter with output directory.
        
        Args:
            output_dir: Directory to save export files
        """
        self.output_dir = output_dir
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def export_to_excel(self, products: List[Dict[str, Any]], 
                       supplier_name: str) -> str:
        """
        Export products to Excel file.
        
        Args:
            products: List of product dictionaries
            supplier_name: Name of supplier (for filename)
            
        Returns:
            Path to the created Excel file
        """
        if not products:
            self.logger.warning("No products to export")
            return ""
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(products)
            
            # Define column order
            column_order = [
                'name',
                'brand',
                'description',
                'price',
                'image',
                'productId',
                'unit',
                'quantity',
                'supplierId'
            ]
            
            # Reorder columns (only include existing ones)
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            # Rename columns to Spanish for consistency with original
            column_mapping = {
                'name': 'Nombre',
                'brand': 'Marca',
                'description': 'Descripción',
                'price': 'Precio',
                'image': 'Imagen',
                'productId': 'Producto ID',
                'unit': 'Unidad',
                'quantity': 'Cantidad',
                'supplierId': 'supplierId'
            }
            
            df.rename(columns=column_mapping, inplace=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_supplier_name = supplier_name.lower().replace(' ', '_')
            filename = f"{safe_supplier_name}_export_{timestamp}.xlsx"
            filepath = os.path.join(self.output_dir, filename)
            
            # Write to Excel
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            self.logger.info(f"Exported {len(products)} products to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to export to Excel: {e}", exc_info=True)
            return ""
    
    def export_to_json(self, products: List[Dict[str, Any]], 
                      supplier_name: str) -> str:
        """
        Export products to JSON file.
        
        Args:
            products: List of product dictionaries
            supplier_name: Name of supplier (for filename)
            
        Returns:
            Path to the created JSON file
        """
        if not products:
            self.logger.warning("No products to export")
            return ""
        
        try:
            import json
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_supplier_name = supplier_name.lower().replace(' ', '_')
            filename = f"{safe_supplier_name}_export_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Exported {len(products)} products to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to export to JSON: {e}", exc_info=True)
            return ""
