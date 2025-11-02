"""Scraping strategies for different website types."""

from .scraping_strategy import ScrapingStrategy
from .selenium_strategy import SeleniumStrategy
from .requests_strategy import RequestsStrategy
from .file_strategy import FileStrategy
from .pdf_strategy import PDFStrategy
from .excel_strategy import ExcelStrategy

__all__ = ['ScrapingStrategy', 'SeleniumStrategy', 'RequestsStrategy', 'FileStrategy', 'PDFStrategy', 'ExcelStrategy']
