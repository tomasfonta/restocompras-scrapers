"""Supplier-specific scraper implementations."""

from .greenshop import GreenShopScraper
from .lacteos_granero import LacteosGraneroScraper
from .distribuidora_pop import DistribuidoraPopScraper
from .tyna import TYNAScraper
from .piala import PialaScraper
from .distribuidora_demarchi import DistribuidoraDeMarchiScraper
from .laduvalina import LaduvalinaScraper
from .labebidadetusfiestas import LaBebidaDeTusFiestasScraper

__all__ = ['GreenShopScraper', 'LacteosGraneroScraper', 'DistribuidoraPopScraper', 'TYNAScraper', 'PialaScraper', 'DistribuidoraDeMarchiScraper', 'LaduvalinaScraper', 'LaBebidaDeTusFiestasScraper']
