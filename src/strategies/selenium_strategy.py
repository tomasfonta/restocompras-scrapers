"""Selenium-based scraping strategy for dynamic websites."""

import time
import logging
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from .scraping_strategy import ScrapingStrategy


class SeleniumStrategy(ScrapingStrategy):
    """
    Scraping strategy using Selenium WebDriver for dynamic content.
    
    Use this strategy for websites that load content dynamically with JavaScript.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Selenium strategy.
        
        Args:
            config: Configuration dictionary with optional keys:
                - headless: Run browser in headless mode (default: True)
                - wait_time: Max wait time for elements (default: 30)
                - scroll_attempts: Number of scroll attempts (default: 3)
                - scroll_delay: Delay between scrolls in seconds (default: 2)
        """
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configuration with defaults
        self.headless = config.get('headless', True)
        self.wait_time = config.get('wait_time', 30)
        self.scroll_attempts = config.get('scroll_attempts', 3)
        self.scroll_delay = config.get('scroll_delay', 2)
        
        # Initialize WebDriver
        self.driver = None
        self._init_driver()
    
    def _init_driver(self) -> None:
        """Initialize Selenium WebDriver with Chrome."""
        try:
            options = webdriver.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=options)
            self.logger.info(f"WebDriver initialized (headless={self.headless})")
            
        except WebDriverException as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def fetch_html(self, url: str) -> str:
        """
        Fetch HTML content using Selenium.
        
        Waits for dynamic content to load and scrolls page to ensure
        all content is rendered.
        
        Args:
            url: URL to fetch
            
        Returns:
            Rendered HTML content as string
            
        Raises:
            TimeoutException: If content doesn't load within wait_time
            WebDriverException: If browser encounters an error
        """
        if self.driver is None:
            raise RuntimeError("WebDriver not initialized")
        
        self.logger.info(f"Fetching URL with Selenium: {url}")
        
        try:
            # Load the page
            self.driver.get(url)
            
            # Wait for initial content to load
            # Note: Supplier implementations should override this with specific selectors
            time.sleep(3)  # Basic wait for page load
            
            # Scroll to load dynamic content
            self._scroll_page()
            
            # Get the rendered HTML
            html_content = self.driver.page_source
            
            self.logger.info(f"Successfully fetched content from {url} ({len(html_content)} bytes)")
            return html_content
            
        except TimeoutException as e:
            self.logger.error(f"Timeout waiting for content at {url}: {e}")
            raise
        except WebDriverException as e:
            self.logger.error(f"WebDriver error at {url}: {e}")
            raise
    
    def wait_for_element(self, selector: str, by: By = By.CSS_SELECTOR) -> None:
        """
        Wait for a specific element to appear on the page.
        
        Args:
            selector: Element selector
            by: Selenium By strategy (default: CSS_SELECTOR)
            
        Raises:
            TimeoutException: If element doesn't appear within wait_time
        """
        self.logger.debug(f"Waiting for element: {selector}")
        
        WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located((by, selector))
        )
        
        self.logger.debug(f"Element found: {selector}")
    
    def _scroll_page(self) -> None:
        """
        Scroll page to trigger lazy loading of content.
        
        Performs multiple scroll attempts with delays to ensure
        all dynamic content is loaded.
        """
        if self.driver is None:
            return
        
        self.logger.debug(f"Scrolling page ({self.scroll_attempts} attempts)")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for attempt in range(self.scroll_attempts):
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for content to load
            time.sleep(self.scroll_delay)
            
            # Check if page height changed (new content loaded)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                self.logger.debug(f"Page height unchanged after scroll {attempt + 1}, stopping")
                break
            
            last_height = new_height
        
        self.logger.debug("Scrolling completed")
    
    def close(self) -> None:
        """Close the WebDriver and clean up resources."""
        if self.driver is not None:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed")
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
