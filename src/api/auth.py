"""
Authentication module for API endpoints.

Provides decorators and utilities to validate API keys using Bearer tokens.
"""
import os
from functools import wraps
from flask import request, jsonify


def get_api_key_secret():
    """
    Retrieve the API key secret from environment.
    
    Returns:
        str: API key secret. Defaults to 'dev-key' if not set (development only).
    """
    return os.getenv('API_KEY_SECRET', 'dev-key')


def validate_api_key(auth_header):
    """
    Validate API key from Authorization header.
    
    Expected format: "Bearer <api-key>"
    
    Args:
        auth_header (str): Authorization header value
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not auth_header:
        return False, "Missing Authorization header"
    
    parts = auth_header.split(' ')
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return False, "Invalid Authorization header format. Expected: 'Bearer <api-key>'"
    
    provided_key = parts[1]
    expected_key = get_api_key_secret()
    
    if provided_key != expected_key:
        return False, "Invalid API key"
    
    return True, "Valid"


def require_api_key(f):
    """
    Decorator to require API key authentication on Flask endpoints.
    
    Usage:
        @app.route('/protected')
        @require_api_key
        def protected_endpoint():
            return "OK"
    
    Returns:
        flask.Response: 401 Unauthorized if authentication fails
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        is_valid, message = validate_api_key(auth_header)
        
        if not is_valid:
            return jsonify({
                'status': 'error',
                'code': 'unauthorized',
                'error': message
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
