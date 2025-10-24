"""Supplier-specific scraper implementations."""

from .greenshop import GreenShopScraper
from .lacteos_granero import LacteosGraneroScraper
from .distribuidora_pop import DistribuidoraPopScraper
from .tyna import TYNAScraper

__all__ = ['GreenShopScraper', 'LacteosGraneroScraper', 'DistribuidoraPopScraper', 'TYNAScraper']
