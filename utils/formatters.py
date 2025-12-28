"""Data formatting utilities for display in templates and charts."""

from datetime import datetime, timedelta
from typing import Union, Optional, Dict, Any


def format_datetime(dt: Union[str, datetime], format: str = '%I:%M %p') -> str:
    """Format datetime for display - handles both datetime objects and strings."""
    if not dt:
        return '--:--'
    
    try:
        if isinstance(dt, datetime):
            return dt.strftime(format)
        
        if isinstance(dt, str):
            try:
                dt_obj = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                return dt_obj.strftime(format)
            except ValueError:
                pass
            
            try:
                dt_obj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                return dt_obj.strftime(format)
            except ValueError:
                pass
            
            return dt[:16] if len(dt) >= 16 else dt
    
    except (ValueError, AttributeError, TypeError):
        return '--:--'


def format_hour_label(hour: int) -> str:
    """Format 24-hour time to 12-hour with AM/PM for chart labels."""
    if hour == 0:
        return '12 AM'
    elif hour < 12:
        return f'{hour} AM'
    elif hour == 12:
        return '12 PM'
    else:
        return f'{hour - 12} PM'


def format_day_label(date: datetime) -> str:
    """Format date relative to today (Today, Yesterday, or full date)."""
    today = datetime.now().date()
    target = date.date()
    
    if target == today:
        return 'Today'
    elif target == today - timedelta(days=1):
        return 'Yesterday'
    elif target == today - timedelta(days=2):
        return '2 days ago'
    elif target == today - timedelta(days=3):
        return '3 days ago'
    else:
        return date.strftime('%B %d, %Y')


def format_date_range(earliest: datetime, latest: datetime) -> str:
    """Format date range for display."""
    if earliest.year == latest.year:
        if earliest.month == latest.month:
            return f"{earliest.strftime('%b %d')}-{latest.strftime('%d, %Y')}"
        else:
            return f"{earliest.strftime('%b %d')} - {latest.strftime('%b %d, %Y')}"
    else:
        return f"{earliest.strftime('%b %d, %Y')} - {latest.strftime('%b %d, %Y')}"


def format_weather_value(value, unit: str = '', decimals: int = 1) -> str:
    """Format weather values for display (handles both numeric and string inputs)."""
    if value is None or value == '':
        return '--'
    
    try:
        numeric_value = float(value) if isinstance(value, str) else float(value)
        formatted = f"{numeric_value:.{decimals}f}"
        if unit:
            formatted += unit
        return formatted
    except (TypeError, ValueError, AttributeError):
        return '--'


def format_sensor_value(
    value: Optional[Union[float, str]],
    unit: str = '',
    decimals: int = 1,
    threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Format sensor value with metadata for UI (display string, validity, threshold checks).
    Handles both numeric and string inputs from API.
    """
    if value is None or value == '':
        return {
            'display': '--',
            'value': None,
            'is_valid': False,
            'exceeds_threshold': False,
            'raw_value': value
        }
    
    try:
        numeric_value = float(value) if isinstance(value, str) else float(value)
        
        display = f"{numeric_value:.{decimals}f}"
        if unit:
            display += unit
        
        exceeds = (threshold is not None and numeric_value >= threshold)
        
        return {
            'display': display,
            'value': numeric_value,
            'is_valid': True,
            'exceeds_threshold': exceeds,
            'raw_value': value
        }
    except (TypeError, ValueError, AttributeError):
        return {
            'display': '--',
            'value': None,
            'is_valid': False,
            'exceeds_threshold': False,
            'raw_value': value
        }


def format_percentage(value: Optional[Union[float, str]], decimals: int = 0) -> str:
    """Format percentage values (handles string inputs from API)."""
    if value is None or value == '':
        return '--%'
    
    try:
        numeric_value = float(value) if isinstance(value, str) else float(value)
        return f"{numeric_value:.{decimals}f}%"
    except (TypeError, ValueError):
        return '--%'


def format_duration(seconds: int) -> str:
    """Format duration in human-readable form (e.g., '1h 5m' or '45s')."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"


def format_file_size(bytes: int) -> str:
    """Format file size in human-readable form (e.g., '1.5 KB' or '2.3 MB')."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"


def format_coordinates(lat: float, lon: float, decimals: int = 6) -> str:
    """Format GPS coordinates for display (e.g., '14.6509°N, 121.1024°E')."""
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    
    return f"{abs(lat):.{decimals}f}°{lat_dir}, {abs(lon):.{decimals}f}°{lon_dir}"
