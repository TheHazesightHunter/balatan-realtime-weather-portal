"""Input validation utilities for the weather portal."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from flask import jsonify


def validate_date_string(date_str: str) -> Tuple[bool, Optional[datetime], Optional[str]]:
    """
    Validate and parse a date string in YYYY-MM-DD format.
    
    Returns:
        Tuple of (is_valid, parsed_date, error_message)
    """
    if not date_str:
        return True, None, None
    
    if len(date_str) != 10:
        return False, None, 'Invalid date format. Use YYYY-MM-DD (e.g., 2024-11-23)'
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return False, None, f'Invalid date: {date_str}. Use YYYY-MM-DD format.'
    
    current_year = datetime.now().year
    if target_date.year < 2020 or target_date.year > current_year + 1:
        return False, None, f'Date must be between 2020 and {current_year + 1}'
    
    if target_date > datetime.now() + timedelta(days=7):
        return False, None, 'Cannot request data more than 7 days in the future'
    
    return True, target_date, None


def create_api_error_response(error_message: str, status_code: int = 400):
    """Create standardized API error response."""
    return jsonify({
        'success': False,
        'error': error_message
    }), status_code


def create_api_success_response(data: dict):
    """Create standardized API success response."""
    response = {'success': True}
    response.update(data)
    return jsonify(response)


def validate_and_get_date(request):
    """
    Validate date from request parameters.
    
    Returns:
        Tuple of (target_date_or_none, error_response_or_none)
    """
    date_str = request.args.get('date')
    is_valid, target_date, error_msg = validate_date_string(date_str)
    
    if not is_valid:
        return None, create_api_error_response(error_msg, 400)
    
    return target_date, None
