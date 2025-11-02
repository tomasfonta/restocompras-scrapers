"""Excel file parsing strategy using openpyxl and pandas."""

import openpyxl
import pandas as pd
import logging
from typing import Dict, Any, List

from .file_strategy import FileStrategy


class ExcelStrategy(FileStrategy):
    """
    Strategy for extracting data from Excel files.
    
    Supports both .xlsx and .xls formats with flexible column mapping.
    Uses pandas for efficient data processing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Excel strategy.
        
        Args:
            config: Configuration dictionary with optional keys:
                - sheet_name: Name or index of sheet to read (default: 0)
                - header_row: Row index for headers (default: 0)
                - skip_rows: Number of rows to skip at start
                - use_pandas: Use pandas for reading (default: True)
        """
        super().__init__(config)
        self.sheet_name = config.get('sheet_name', 0)
        self.header_row = config.get('header_row', 0)
        self.skip_rows = config.get('skip_rows', None)
        self.use_pandas = config.get('use_pandas', True)
        
        self.logger.info("Excel strategy initialized")
    
    def extract_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract structured data from Excel file.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of dictionaries with extracted data
            
        Raises:
            Exception: If Excel extraction fails
        """
        self.logger.info(f"Extracting data from Excel: {file_path}")
        
        try:
            if self.use_pandas:
                data = self._extract_with_pandas(file_path)
            else:
                data = self._extract_with_openpyxl(file_path)
            
            self.logger.info(f"Extracted {len(data)} rows from Excel")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to extract data from Excel: {e}", exc_info=True)
            raise
    
    def _extract_with_pandas(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract data using pandas.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of row dictionaries
        """
        # Read Excel file
        df = pd.read_excel(
            file_path,
            sheet_name=self.sheet_name,
            header=self.header_row,
            skiprows=self.skip_rows
        )
        
        # Clean column names only if they're strings
        if all(isinstance(col, str) for col in df.columns):
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        else:
            # If columns are not strings (e.g., integers), keep them as-is
            pass
        
        # Replace NaN with empty strings
        df = df.fillna('')
        
        # Convert to list of dictionaries
        data = df.to_dict('records')
        
        # Add row numbers
        for idx, row in enumerate(data, 1):
            row['_row'] = idx
        
        return data
    
    def _extract_with_openpyxl(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract data using openpyxl (lower-level, more control).
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of row dictionaries
        """
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        
        # Get sheet
        if isinstance(self.sheet_name, int):
            sheet = workbook.worksheets[self.sheet_name]
        else:
            sheet = workbook[self.sheet_name]
        
        data = []
        
        # Get header row
        header_row_idx = self.header_row + 1  # openpyxl is 1-indexed
        headers = []
        
        for cell in sheet[header_row_idx]:
            header = str(cell.value).strip().lower().replace(' ', '_') if cell.value else ''
            headers.append(header)
        
        # Process data rows
        start_row = header_row_idx + 1
        if self.skip_rows:
            start_row += self.skip_rows
        
        for row_idx, row in enumerate(sheet.iter_rows(min_row=start_row, values_only=True), 1):
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue
            
            row_dict = {}
            for header, value in zip(headers, row):
                if header:
                    row_dict[header] = str(value).strip() if value else ''
            
            row_dict['_row'] = row_idx
            data.append(row_dict)
        
        workbook.close()
        return data
    
    def close(self) -> None:
        """Clean up resources."""
        self.logger.info("Excel strategy closed")
