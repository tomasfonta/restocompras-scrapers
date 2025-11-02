"""PDF parsing strategy using pdfplumber."""

import pdfplumber
import logging
from typing import Dict, Any, List
import re

from .file_strategy import FileStrategy


class PDFStrategy(FileStrategy):
    """
    Strategy for extracting data from PDF files using pdfplumber.
    
    Supports table extraction and text parsing from PDF price lists.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PDF strategy.
        
        Args:
            config: Configuration dictionary with optional keys:
                - table_settings: pdfplumber table extraction settings
                - page_range: Tuple of (start_page, end_page) to parse
                - text_mode: If True, extract text instead of tables
        """
        super().__init__(config)
        self.table_settings = config.get('table_settings', {})
        self.page_range = config.get('page_range', None)
        self.text_mode = config.get('text_mode', False)
        
        self.logger.info("PDF strategy initialized")
    
    def extract_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract structured data from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of dictionaries with extracted data
            
        Raises:
            Exception: If PDF extraction fails
        """
        self.logger.info(f"Extracting data from PDF: {file_path}")
        
        all_data = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                pages = pdf.pages
                
                # Apply page range filter if specified
                if self.page_range:
                    start, end = self.page_range
                    pages = pages[start-1:end]
                
                self.logger.info(f"Processing {len(pages)} pages from PDF")
                
                for page_num, page in enumerate(pages, 1):
                    self.logger.debug(f"Processing page {page_num}")
                    
                    if self.text_mode:
                        # Extract text mode
                        page_data = self._extract_text_data(page, page_num)
                    else:
                        # Extract tables mode
                        page_data = self._extract_table_data(page, page_num)
                    
                    all_data.extend(page_data)
                
                self.logger.info(f"Extracted {len(all_data)} rows from PDF")
                
        except Exception as e:
            self.logger.error(f"Failed to extract data from PDF: {e}", exc_info=True)
            raise
        
        return all_data
    
    def _extract_table_data(self, page, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract data from tables in PDF page.
        
        Args:
            page: pdfplumber page object
            page_num: Page number for logging
            
        Returns:
            List of row dictionaries
        """
        page_data = []
        
        try:
            # Extract tables from page
            tables = page.extract_tables(table_settings=self.table_settings)
            
            if not tables:
                self.logger.debug(f"No tables found on page {page_num}")
                return page_data
            
            for table_idx, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue
                
                # First row is typically headers
                headers = table[0]
                
                # Process data rows
                for row_idx, row in enumerate(table[1:], 1):
                    if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                        continue
                    
                    # Create dictionary mapping headers to values
                    row_dict = {}
                    for col_idx, (header, value) in enumerate(zip(headers, row)):
                        if header:
                            clean_header = str(header).strip().lower().replace(' ', '_')
                            row_dict[clean_header] = str(value).strip() if value else ''
                    
                    row_dict['_page'] = page_num
                    row_dict['_table'] = table_idx + 1
                    row_dict['_row'] = row_idx
                    
                    page_data.append(row_dict)
            
        except Exception as e:
            self.logger.warning(f"Error extracting tables from page {page_num}: {e}")
        
        return page_data
    
    def _extract_text_data(self, page, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract data from text in PDF page.
        
        Args:
            page: pdfplumber page object
            page_num: Page number for logging
            
        Returns:
            List of text line dictionaries
        """
        page_data = []
        
        try:
            text = page.extract_text()
            
            if not text:
                self.logger.debug(f"No text found on page {page_num}")
                return page_data
            
            # Split into lines
            lines = text.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                page_data.append({
                    'text': line,
                    '_page': page_num,
                    '_line': line_num
                })
        
        except Exception as e:
            self.logger.warning(f"Error extracting text from page {page_num}: {e}")
        
        return page_data
    
    def close(self) -> None:
        """Clean up resources."""
        self.logger.info("PDF strategy closed")
