"""
Flask API for restoCompras Scrapers.

Exposes HTTP endpoints to execute scraping operations dynamically
and return results as JSON without persisting to files.

Usage:
    Set environment variables:
        export API_KEY_SECRET="your-secret-key"
        export FLASK_ENV=dev
        export FLASK_PORT=5000
    
    Then run:
        python app.py
    
    API Key is passed as: Authorization: Bearer <api-key>
"""
import os
import logging
from datetime import datetime
from typing import Tuple

from flask import Flask, jsonify, request
from dotenv import load_dotenv

from src.api.auth import require_api_key
from src.api.scraper_engine import scrape_supplier_only, get_available_suppliers
from src.utils import setup_logger


# Load environment variables from .env file
load_dotenv()

# Create Flask application
app = Flask(__name__)

# Configure logging
log_dir = os.getenv('LOG_DIR', 'logs')
log_level = os.getenv('LOG_LEVEL', 'INFO')
logger = setup_logger(log_dir=log_dir, level=getattr(logging, log_level, logging.INFO))

# Configuration from environment
app.config['ENV'] = os.getenv('FLASK_ENV', 'development')
app.config['DEBUG'] = app.config['ENV'] == 'dev'
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
CONFIG_DIR = os.getenv('CONFIG_DIR', 'configs')
ENVIRONMENT = os.getenv('ENV', 'dev')


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint (no authentication required).
    
    Returns:
        JSON with service status
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'restocompras-scrapers-api'
    }), 200


@app.route('/api/suppliers', methods=['GET'])
@require_api_key
def list_suppliers():
    """
    List all available suppliers.
    
    Requires authentication via Bearer token.
    
    Returns:
        JSON with list of supplier names
    """
    try:
        suppliers = get_available_suppliers()
        return jsonify({
            'status': 'success',
            'suppliers': suppliers,
            'count': len(suppliers)
        }), 200
    except Exception as e:
        logger.error(f"Error listing suppliers: {e}")
        return jsonify({
            'status': 'error',
            'code': 'internal_error',
            'error': 'Failed to list suppliers'
        }), 500


@app.route('/api/scrape/<supplier_name>', methods=['POST'])
def scrape_supplier(supplier_name: str):
    """
    Scrape products for a specific supplier.
    
    Executes scraping operation without persistence to files or database.
    Returns items as JSON array.
    
    Path Parameters:
        supplier_name (str): Name of supplier to scrape (e.g., 'delparque', 'greenshop')
    
    Headers:
        (No authentication required - public endpoint)
    
    Returns:
        JSON response with items or error details
        
    Success Response (200 OK):
        {
            "status": "success",
            "supplier": "delparque",
            "supplier_id": 47,
            "supplier_name": "Del Parque Bebidas",
            "item_count": 42,
            "items": [
                {
                    "name": "Bebida 500ml",
                    "price": 150.50,
                    "brand": "Del Parque",
                    "description": "...",
                    "image": "https://...",
                    "productId": 123,
                    "unit": "ML",
                    "quantity": 500,
                    "supplierId": 47
                },
                ...
            ]
        }
    
    Error Responses:
        400 Bad Request: Invalid supplier name
        401 Unauthorized: Invalid or missing API key
        404 Not Found: Supplier doesn't exist
        500 Internal Server Error: Scraping failed
    """
    # Normalize supplier name (lowercase)
    supplier_name_normalized = supplier_name.lower()
    
    logger.info(f"API Request: Scraping {supplier_name_normalized}")
    
    try:
        # Execute scraping
        success, result = scrape_supplier_only(
            supplier_name=supplier_name_normalized,
            config_dir=CONFIG_DIR,
            log_dir=log_dir,
            environment=ENVIRONMENT,
            logger=logger
        )
        
        if success:
            logger.info(f"Scraping succeeded: {supplier_name_normalized}, items: {result.get('item_count', 0)}")
            return jsonify(result), 200
        else:
            # Handle different error codes
            error_code = result.get('code', 'unknown_error')
            
            if error_code == 'supplier_not_found':
                logger.warning(f"Supplier not found: {supplier_name_normalized}")
                return jsonify(result), 404
            elif error_code == 'config_not_found':
                logger.error(f"Config not found for: {supplier_name_normalized}")
                return jsonify(result), 404
            elif error_code == 'scrape_failed':
                logger.error(f"Scraping failed for: {supplier_name_normalized}")
                return jsonify(result), 500
            else:
                logger.error(f"Unknown error for: {supplier_name_normalized}")
                return jsonify(result), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in scrape endpoint: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'code': 'internal_error',
            'error': 'Unexpected server error'
        }), 500


@app.route('/api/scrape', methods=['GET'])
def scrape_usage():
    """
    Usage information for scraping endpoint.
    
    Returns:
        JSON with endpoint documentation
    """
    return jsonify({
        'status': 'info',
        'message': 'Use POST /api/scrape/<supplier_name> to scrape a supplier',
        'example': {
            'method': 'POST',
            'url': '/api/scrape/delparque',
            'headers': {
                'Authorization': 'Bearer your-api-key-here'
            },
            'response': {
                'status': 'success',
                'supplier': 'delparque',
                'item_count': 42,
                'items': []
            }
        },
        'available_suppliers': get_available_suppliers()
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 - Not Found errors."""
    return jsonify({
        'status': 'error',
        'code': 'not_found',
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 - Method Not Allowed errors."""
    return jsonify({
        'status': 'error',
        'code': 'method_not_allowed',
        'error': 'HTTP method not allowed for this endpoint'
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 - Internal Server Error."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'code': 'internal_error',
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    # Log startup information
    logger.info("="*70)
    logger.info("restoCompras Scrapers API - Starting...")
    logger.info("="*70)
    logger.info(f"Flask Environment: {app.config['ENV']}")
    logger.info(f"Port: {FLASK_PORT}")
    logger.info(f"Config Directory: {CONFIG_DIR}")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info("Available endpoints:")
    logger.info("  GET  /health                    - Health check (no auth)")
    logger.info("  GET  /api/scrape                - Usage info (no auth)")
    logger.info("  GET  /api/suppliers             - List suppliers (requires API key)")
    logger.info("  POST /api/scrape/<supplier>     - Scrape supplier (no auth - public)")
    logger.info("="*70)
    
    # Run Flask app
    app.run(
        host='127.0.0.1',
        port=FLASK_PORT,
        debug=app.config['DEBUG']
    )
