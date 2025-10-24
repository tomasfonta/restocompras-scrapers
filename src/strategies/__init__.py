"""Scraping strategies for different website types."""

from .scraping_strategy import ScrapingStrategy
from .selenium_strategy import SeleniumStrategy
from .requests_strategy import RequestsStrategy

__all__ = ['ScrapingStrategy', 'SeleniumStrategy', 'RequestsStrategy']
