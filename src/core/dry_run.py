"""Dry-run mode module for testing scrapers without API submission.

Allows testing scrapers locally and previewing items that would be
submitted before actually posting to the backend API.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class DryRunResult:
    """Result from a dry-run item build."""
    item: Dict[str, Any]
    product_name: str
    product_id: int
    success: bool
    errors: List[str]
    warnings: List[str]
    timestamp: str


class DryRunMode:
    """
    Simulates item submission without actually calling the API.
    
    Useful for:
    - Testing scraper configuration changes
    - Validating item transformations
    - Previewing what will be posted
    - Debugging integration issues
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        Initialize dry-run mode.
        
        Args:
            enable_logging: Whether to log dry-run operations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enable_logging = enable_logging
        self.results = []
        self.mock_product_ids = {}  # Map of product_name -> mock_id
        self._next_mock_id = 1000  # Start mock IDs at 1000
    
    def build_item_dry_run(self, item_builder: 'ItemBuilder', product_data: Dict[str, Any], 
                           product_id: Optional[int] = None) -> DryRunResult:
        """
        Build item in dry-run mode (no API call).
        
        Args:
            item_builder: ItemBuilder instance to use
            product_data: Raw scraped product data
            product_id: Optional product ID. If None, uses mock ID
            
        Returns:
            DryRunResult with success status and any issues
        """
        product_name = product_data.get('name', 'Unknown')
        
        # Use provided product_id or generate mock
        if product_id is None:
            product_id = self._get_or_create_mock_product_id(product_name)
        
        result = DryRunResult(
            item={},
            product_name=product_name,
            product_id=product_id,
            success=False,
            errors=[],
            warnings=[],
            timestamp=datetime.now().isoformat()
        )
        
        try:
            # Build item using ItemBuilder
            item = item_builder.build_item(product_data, product_id)
            
            if item is None:
                result.errors.append("ItemBuilder returned None (validation failed)")
                self.logger.warning(f"Dry-run: Item build failed for '{product_name}'")
                self.results.append(result)
                return result
            
            result.item = item
            result.success = True
            
            if self.enable_logging:
                self.logger.info(
                    f"Dry-run ✅ Built item: {product_name} → "
                    f"${item.get('price', 0):.2f}, {item.get('quantity', 0)}{item.get('unit', 'U')}"
                )
            
        except Exception as e:
            result.errors.append(f"Exception during build: {str(e)}")
            self.logger.error(f"Dry-run ❌ Error building item for '{product_name}': {e}", exc_info=True)
        
        self.results.append(result)
        return result
    
    def validate_items_dry_run(self, items: List[Dict[str, Any]], validator: 'ItemValidator') -> Dict[str, Any]:
        """
        Validate multiple items in dry-run mode.
        
        Args:
            items: List of items to validate
            validator: ItemValidator instance
            
        Returns:
            Validation report
        """
        report = validator.validate_batch(items)
        
        if self.enable_logging:
            self.logger.info(
                f"Dry-run validation: {report['valid_items']}/{report['total_items']} valid, "
                f"{report['items_with_errors']} errors, {report['items_with_warnings']} warnings"
            )
        
        return report
    
    def simulate_api_post(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate posting an item to API (returns mock response).
        
        Args:
            item: Item to simulate posting
            
        Returns:
            Mock API response
        """
        # Simulate successful API response
        mock_item_id = hash(item.get('name', 'unknown')) % 999999 + 1000000
        
        return {
            'id': mock_item_id,
            'name': item.get('name'),
            'price': item.get('price'),
            'productId': item.get('productId'),
            'supplierId': item.get('supplierId'),
            'createdAt': datetime.now().isoformat(),
            'status': 'ACTIVE'
        }
    
    def preview_batch(self, items: List[Dict[str, Any]]) -> str:
        """
        Generate human-readable preview of items to be posted.
        
        Args:
            items: List of items to preview
            
        Returns:
            Formatted preview string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"DRY-RUN PREVIEW: {len(items)} items to be posted")
        lines.append("=" * 80)
        
        total_value = 0.0
        
        for idx, item in enumerate(items, 1):
            name = item.get('name', 'Unknown')[:50]
            price = item.get('price', 0)
            qty = item.get('quantity', 0)
            unit = item.get('unit', 'U')
            product_id = item.get('productId', '?')
            
            total_value += price * qty
            
            lines.append(f"\n[{idx:3d}] {name}")
            lines.append(f"       Price: ${price:>10.2f} | Qty: {qty:>6.2f} {unit:<3} | Product ID: {product_id}")
            lines.append(f"       Brand: {item.get('brand', 'N/A')}")
            lines.append(f"       Desc:  {item.get('description', 'N/A')[:40]}")
        
        lines.append("\n" + "=" * 80)
        lines.append(f"Summary: {len(items)} items, Total value: ${total_value:,.2f}")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def get_mock_product_id(self, product_name: str) -> int:
        """Get or create a mock product ID for testing."""
        return self._get_or_create_mock_product_id(product_name)
    
    def _get_or_create_mock_product_id(self, product_name: str) -> int:
        """Get or create mock product ID (cached)."""
        if product_name not in self.mock_product_ids:
            self.mock_product_ids[product_name] = self._next_mock_id
            self._next_mock_id += 1
        return self.mock_product_ids[product_name]
    
    def export_dry_run_results(self, filepath: str) -> None:
        """
        Export dry-run results to JSON file for inspection.
        
        Args:
            filepath: Path to save JSON file
        """
        # Convert dataclass results to dicts
        results_data = [asdict(r) for r in self.results]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Dry-run results exported to {filepath}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of dry-run results."""
        if not self.results:
            return {
                'total_runs': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'mock_product_ids_created': 0
            }
        
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        
        return {
            'total_runs': len(self.results),
            'successful': successful,
            'failed': failed,
            'success_rate': successful / len(self.results) * 100 if self.results else 0,
            'mock_product_ids_created': len(self.mock_product_ids),
            'total_mock_ids': list(range(1000, self._next_mock_id))
        }
    
    def print_summary(self) -> None:
        """Print dry-run summary to logger."""
        summary = self.get_summary()
        
        self.logger.info("=" * 70)
        self.logger.info("DRY-RUN SUMMARY")
        self.logger.info("=" * 70)
        self.logger.info(f"Total Runs:        {summary['total_runs']}")
        self.logger.info(f"Successful:        {summary['successful']} ✅")
        self.logger.info(f"Failed:            {summary['failed']} ❌")
        self.logger.info(f"Success Rate:      {summary['success_rate']:.1f}%")
        self.logger.info(f"Mock IDs Created:  {summary['mock_product_ids_created']}")
        self.logger.info("=" * 70)


class DryRunApiClient:
    """
    Mock API client that simulates backend responses for dry-run testing.
    
    Can be used as a drop-in replacement for real APIClient during dry-run.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize mock API client.
        
        Args:
            verbose: Whether to log mock API calls
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.verbose = verbose
        self.call_log = []
        self._next_product_id = 500  # Mock product IDs start at 500
        self._next_supplier_id = 50  # Mock supplier IDs start at 50
    
    def login(self) -> Optional[str]:
        """Mock login - returns fake token."""
        token = "mock_jwt_token_for_testing_12345"
        if self.verbose:
            self.logger.info(f"[MOCK] Login successful - token: {token[:20]}...")
        self.call_log.append(('login', {}))
        return token
    
    def fetch_supplier_details(self, email: str) -> Optional[Dict[str, Any]]:
        """Mock supplier fetch."""
        supplier = {
            'id': self._next_supplier_id,
            'name': 'Test Supplier',
            'email': email,
            'status': 'ACTIVE'
        }
        if self.verbose:
            self.logger.info(f"[MOCK] Fetched supplier: {supplier['name']} (ID: {supplier['id']})")
        self.call_log.append(('fetch_supplier', {'email': email}))
        return supplier
    
    def fetch_product_id(self, product_name: str) -> Optional[int]:
        """Mock product ID fetch."""
        product_id = hash(product_name) % 999 + 100  # Generate consistent ID per name
        if self.verbose:
            self.logger.info(f"[MOCK] Found product ID {product_id} for '{product_name}'")
        self.call_log.append(('fetch_product_id', {'product_name': product_name}))
        return product_id
    
    def post_item(self, product_data: Dict[str, Any]) -> bool:
        """Mock item posting - always succeeds."""
        if self.verbose:
            self.logger.info(f"[MOCK] Posted item: {product_data.get('name')}")
        self.call_log.append(('post_item', {'name': product_data.get('name')}))
        return True
    
    def delete_supplier_items(self, supplier_id: int) -> bool:
        """Mock item deletion."""
        if self.verbose:
            self.logger.info(f"[MOCK] Deleted items for supplier {supplier_id}")
        self.call_log.append(('delete_supplier_items', {'supplier_id': supplier_id}))
        return True
    
    def get_call_log(self) -> List[tuple]:
        """Get log of all mock API calls."""
        return self.call_log
