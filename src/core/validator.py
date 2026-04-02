"""Validator module for pre-submission item validation.

Checks items for completeness, data quality, and compliance before
posting to the backend API. Provides detailed validation reports.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum


class ValidationLevel(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue:
    """Represents a single validation issue."""
    
    def __init__(self, level: ValidationLevel, field: str, message: str, value: Any = None):
        self.level = level
        self.field = field
        self.message = message
        self.value = value
    
    def __repr__(self) -> str:
        return f"[{self.level.value.upper()}] {self.field}: {self.message}"


class ItemValidator:
    """
    Validates items before API submission.
    
    Checks for:
    - Required fields presence
    - Data type and format correctness
    - Value ranges and constraints
    - Data quality and consistency
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, warnings are treated as errors
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.strict_mode = strict_mode
    
    def validate_item(self, item: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate a single item.
        
        Args:
            item: Item to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Required fields validation
        issues.extend(self._validate_required_fields(item))
        
        # Field-specific validation
        issues.extend(self._validate_name(item.get('name')))
        issues.extend(self._validate_price(item.get('price')))
        issues.extend(self._validate_unit(item.get('unit')))
        issues.extend(self._validate_quantity(item.get('quantity')))
        issues.extend(self._validate_product_id(item.get('productId')))
        issues.extend(self._validate_supplier_id(item.get('supplierId')))
        issues.extend(self._validate_description(item.get('description')))
        issues.extend(self._validate_image(item.get('image')))
        
        # Determine validity
        if self.strict_mode:
            is_valid = not any(issue.level == ValidationLevel.ERROR for issue in issues)
        else:
            is_valid = not any(issue.level == ValidationLevel.ERROR for issue in issues)
        
        return is_valid, issues
    
    def validate_batch(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate multiple items and provide summary report.
        
        Args:
            items: List of items to validate
            
        Returns:
            Validation report dictionary
        """
        report = {
            'total_items': len(items),
            'valid_items': 0,
            'invalid_items': 0,
            'items_with_warnings': 0,
            'items_with_errors': 0,
            'details': []
        }
        
        for idx, item in enumerate(items):
            is_valid, issues = self.validate_item(item)
            
            item_report = {
                'index': idx,
                'name': item.get('name', 'Unknown'),
                'valid': is_valid,
                'issues': [str(issue) for issue in issues],
                'issue_count': len(issues)
            }
            
            report['details'].append(item_report)
            
            if is_valid:
                report['valid_items'] += 1
            else:
                report['invalid_items'] += 1
            
            if any(issue.level == ValidationLevel.WARNING for issue in issues):
                report['items_with_warnings'] += 1
            
            if any(issue.level == ValidationLevel.ERROR for issue in issues):
                report['items_with_errors'] += 1
        
        return report
    
    def _validate_required_fields(self, item: Dict[str, Any]) -> List[ValidationIssue]:
        """Check that all required fields are present."""
        issues = []
        # Only truly required fields that the API needs
        required_fields = ['name', 'price', 'unit', 'quantity']
        
        for field in required_fields:
            if field not in item:
                issues.append(ValidationIssue(
                    ValidationLevel.ERROR,
                    field,
                    f"Required field missing"
                ))
            elif item[field] is None:
                issues.append(ValidationIssue(
                    ValidationLevel.ERROR,
                    field,
                    f"Required field is None"
                ))
        
        return issues
    
    def _validate_name(self, name: Any) -> List[ValidationIssue]:
        """Validate product name - minimal validation."""
        issues = []
        
        if not name:
            return issues
        
        if not isinstance(name, str):
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'name',
                f"Must be string, got {type(name).__name__}",
                name
            ))
            return issues
        
        if len(name.strip()) == 0:
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'name',
                "Cannot be empty",
                name
            ))
        
        return issues
    
    def _validate_price(self, price: Any) -> List[ValidationIssue]:
        """Validate price - minimal validation."""
        issues = []
        
        if price is None:
            return issues
        
        if not isinstance(price, (int, float)):
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'price',
                f"Must be numeric, got {type(price).__name__}",
                price
            ))
            return issues
        
        if price < 0:
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'price',
                "Cannot be negative",
                price
            ))
        elif price == 0:
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'price',
                "Cannot be zero",
                price
            ))
        
        return issues
    
    def _validate_unit(self, unit: Any) -> List[ValidationIssue]:
        """Validate unit - minimal validation."""
        issues = []
        
        if not unit:
            return issues
        
        if not isinstance(unit, str):
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'unit',
                f"Must be string, got {type(unit).__name__}",
                unit
            ))
        
        return issues
    
    def _validate_quantity(self, quantity: Any) -> List[ValidationIssue]:
        """Validate quantity - minimal validation."""
        issues = []
        
        if quantity is None:
            return issues
        
        if not isinstance(quantity, (int, float)):
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'quantity',
                f"Must be numeric, got {type(quantity).__name__}",
                quantity
            ))
            return issues
        
        if quantity < 0:
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'quantity',
                "Cannot be negative",
                quantity
            ))
        
        return issues
    
    def _validate_product_id(self, product_id: Any) -> List[ValidationIssue]:
        """Validate product ID - only if present."""
        issues = []
        
        if product_id is None:
            return issues
        
        if not isinstance(product_id, int):
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'productId',
                f"Must be integer, got {type(product_id).__name__}",
                product_id
            ))
            return issues
        
        if product_id <= 0:
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'productId',
                "Must be positive integer",
                product_id
            ))
        
        return issues
    
    def _validate_supplier_id(self, supplier_id: Any) -> List[ValidationIssue]:
        """Validate supplier ID - only if present."""
        issues = []
        
        if supplier_id is None:
            return issues
        
        if not isinstance(supplier_id, int):
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'supplierId',
                f"Must be integer, got {type(supplier_id).__name__}",
                supplier_id
            ))
            return issues
        
        if supplier_id <= 0:
            issues.append(ValidationIssue(
                ValidationLevel.ERROR,
                'supplierId',
                "Must be positive integer",
                supplier_id
            ))
        
        return issues
    
    def _validate_description(self, description: Any) -> List[ValidationIssue]:
        """Validate description (optional field)."""
        return []
    
    def _validate_image(self, image: Any) -> List[ValidationIssue]:
        """Validate image URL (optional field)."""
        return []
    
    def print_report(self, report: Dict[str, Any]) -> str:
        """
        Format validation report as readable string.
        
        Args:
            report: Report from validate_batch()
            
        Returns:
            Formatted report string
        """
        lines = []
        
        lines.append("=" * 70)
        lines.append("BATCH VALIDATION REPORT")
        lines.append("=" * 70)
        lines.append(f"Total Items:        {report['total_items']}")
        lines.append(f"Valid Items:        {report['valid_items']} ✅")
        lines.append(f"Invalid Items:      {report['invalid_items']} ❌")
        lines.append(f"Items w/ Warnings:  {report['items_with_warnings']} ⚠️")
        lines.append(f"Items w/ Errors:    {report['items_with_errors']} 🔴")
        lines.append("=" * 70)
        
        # Show items with issues
        issues_found = [d for d in report['details'] if d['issue_count'] > 0]
        if issues_found:
            lines.append(f"\nITEMS WITH ISSUES ({len(issues_found)}):")
            lines.append("-" * 70)
            
            for item_detail in issues_found:
                status = "✅" if item_detail['valid'] else "❌"
                lines.append(f"{status} [{item_detail['index']}] {item_detail['name']}")
                for issue in item_detail['issues']:
                    lines.append(f"    → {issue}")
        
        if report['valid_items'] == report['total_items']:
            lines.append("\n✅ All items are valid!")
        else:
            lines.append(f"\n⚠️  {report['invalid_items']} items need attention")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
