"""API routes for JSON endpoints with caching support."""

import logging
from datetime import datetime
from flask import Blueprint, request, current_app
from config import UIColorSystem, ChartConfig, ColorAPI
from utils.validators import (
    validate_and_get_date,
    create_api_error_response,
    create_api_success_response
)
from utils.error_handlers import handle_api_errors

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)


@api_bp.route('/config/stations')
@handle_api_errors
def station_config():
    """Get station configuration and chart settings."""
    stations = [
        {
            'id': site['id'],
            'name': site['name'],
            'color': UIColorSystem.STATION_COLORS.get(site['id'], UIColorSystem.PRIMARY)
        }
        for site in current_app.config['SITES']
    ]

    return create_api_success_response({
        'stations': stations,
        'chart_config': {
            'ICON_INTERVAL': ChartConfig.ICON_INTERVAL,
            'ICON_SIZE': ChartConfig.ICON_SIZE,
            'LABEL_INTERVAL': ChartConfig.LABEL_INTERVAL,
        }
    })


@api_bp.route('/config/complete')
@handle_api_errors
def complete_config():
    """Return complete configuration for frontend JavaScript."""
    try:
        from config import get_complete_config
        config_data = get_complete_config()
        config_data['api_url'] = current_app.config['API_URL']
        config_data['api_timeout'] = current_app.config['API_TIMEOUT']
        config_data['debug_mode'] = current_app.debug
        config_data['generated_at'] = datetime.now().isoformat()
        
        return create_api_success_response(config_data)
        
    except Exception as e:
        logger.error("Failed to load complete config: %s", str(e), exc_info=True)
        return create_api_error_response(
            'Configuration service temporarily unavailable',
            503
        )


@api_bp.route('/css-variables')
@handle_api_errors
def css_variables_api():
    """Serve CSS variables for JavaScript consumption."""
    try:
        return create_api_success_response(ColorAPI.get_javascript_config())
    except Exception as e:
        logger.error("Failed to load CSS variables: %s", str(e))
        return create_api_error_response("Color configuration unavailable", 500)


@api_bp.route('/health')
def health_check():
    """Health check endpoint with cache status."""
    try:
        cache_status = current_app.weather_service.get_cache_status()
        weather_data = current_app.weather_service.fetch_weather_data()
        api_status = "healthy" if weather_data else "degraded"
        
        health_status = {
            "status": "healthy" if api_status == "healthy" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "api": api_status,
                "weather_service": "healthy",
                "config": "healthy"
            },
            "cache": cache_status,
            "stations_count": len(current_app.config['SITES'])
        }
        
        status_code = 200 if api_status == "healthy" else 503
        return create_api_success_response(health_status), status_code
        
    except Exception as e:
        logger.error("Health check failed: %s", str(e), exc_info=True)
        return create_api_error_response('System health check failed', 503)


@api_bp.route('/weather-data')
@handle_api_errors
def weather_data():
    """
    Get weather data with cache support.
    Returns cached data when external API is unavailable.
    """
    station_id = request.args.get('station_id')
    force_refresh = request.args.get('refresh', '').lower() == 'true'
    
    try:
        weather_data = current_app.weather_service.fetch_weather_data(force_refresh=force_refresh)
        cache_status = current_app.weather_service.get_cache_status()
        
        if not weather_data:
            logger.warning("No weather data available")
            return create_api_error_response(
                'Weather data temporarily unavailable. Please try again.',
                503
            )
        
        if station_id:
            weather_data = [d for d in weather_data if d.get('StationID') == station_id]
        
        response_data = {
            'data': weather_data,
            'count': len(weather_data),
            'station_id': station_id,
            'generated_at': datetime.now().isoformat(),
            'cache_status': {
                'is_cached': cache_status.get('age_seconds', 0) > 5,
                'age_seconds': cache_status.get('age_seconds'),
                'last_success': cache_status.get('last_success')
            }
        }
        
        return create_api_success_response(response_data)
        
    except Exception as e:
        logger.error("Weather data endpoint error: %s", str(e), exc_info=True)
        return create_api_error_response('Failed to fetch weather data', 503)


@api_bp.route('/precipitation-data')
@handle_api_errors
def precipitation_data():
    """Get 24-hour precipitation data with caching."""
    target_date, error_response = validate_and_get_date(request)
    if error_response:
        return error_response

    station_id = request.args.get('station_id')

    weather_data = current_app.weather_service.fetch_weather_data()
    cache_status = current_app.weather_service.get_cache_status()
    
    if not weather_data:
        return create_api_error_response(
            'Weather data temporarily unavailable. Please try again.',
            503
        )

    per_station_data = current_app.precipitation_service.get_24hour_intervals_per_station(
        weather_data=weather_data,
        sites=current_app.config['SITES'],
        target_date=target_date
    )

    if station_id:
        per_station_data = {k: v for k, v in per_station_data.items() if k == station_id}

    stations_response = _format_precipitation_response(
        per_station_data,
        current_app.config['SITES']
    )

    display_date = target_date or datetime.now()
    return create_api_success_response({
        'stations': stations_response,
        'unit': 'mm/hour',
        'interval': '1 hour',
        'date': display_date.strftime('%Y-%m-%d'),
        'date_display': display_date.strftime('%B %d, %Y'),
        'station_id': station_id,
        'generated_at': datetime.now().isoformat(),
        'cache_status': {
            'is_cached': cache_status.get('age_seconds', 0) > 5,
            'age_seconds': cache_status.get('age_seconds')
        }
    })


@api_bp.route('/precipitation-date-range')
@handle_api_errors
def precipitation_date_range():
    """Get available date range for precipitation data."""
    weather_data = current_app.weather_service.fetch_weather_data()
    if not weather_data:
        return create_api_error_response('No weather data available', 503)

    date_range = current_app.precipitation_service.get_available_date_range(weather_data)
    if not date_range:
        return create_api_error_response('No valid timestamps in data', 503)

    total_days = (date_range['latest'] - date_range['earliest']).days + 1

    return create_api_success_response({
        'earliest_date': date_range['earliest'].strftime('%Y-%m-%d'),
        'latest_date': date_range['latest'].strftime('%Y-%m-%d'),
        'earliest_display': date_range['earliest'].strftime('%B %d, %Y'),
        'latest_display': date_range['latest'].strftime('%B %d, %Y'),
        'total_days': total_days
    })


@api_bp.route('/water-level-data')
@handle_api_errors
def water_level_data():
    """Get 24-hour water level data with caching."""
    target_date, error_response = validate_and_get_date(request)
    if error_response:
        return error_response

    station_id = request.args.get('station_id')

    weather_data = current_app.weather_service.fetch_weather_data()
    cache_status = current_app.weather_service.get_cache_status()
    
    if not weather_data:
        return create_api_error_response(
            'Weather data temporarily unavailable. Please try again.',
            503
        )

    per_station_data = current_app.water_level_service.get_24hour_intervals_per_station(
        weather_data=weather_data,
        sites=current_app.config['SITES'],
        target_date=target_date
    )

    if station_id:
        per_station_data = {k: v for k, v in per_station_data.items() if k == station_id}

    stations_response = _format_water_level_response(
        per_station_data,
        current_app.config['SITES'],
        current_app.water_level_service
    )

    display_date = target_date or datetime.now()
    return create_api_success_response({
        'stations': stations_response,
        'unit': 'centimeters',
        'interval': '1 hour',
        'date': display_date.strftime('%Y-%m-%d'),
        'date_display': display_date.strftime('%B %d, %Y'),
        'station_id': station_id,
        'generated_at': datetime.now().isoformat(),
        'cache_status': {
            'is_cached': cache_status.get('age_seconds', 0) > 5,
            'age_seconds': cache_status.get('age_seconds')
        }
    })


@api_bp.route('/water-level-date-range')
@handle_api_errors
def water_level_date_range():
    """Get available date range for water level data."""
    weather_data = current_app.weather_service.fetch_weather_data()
    if not weather_data:
        return create_api_error_response('No weather data available', 503)

    date_range = current_app.water_level_service.get_available_date_range(weather_data)
    if not date_range:
        return create_api_error_response('No valid timestamps in data', 503)

    total_days = (date_range['latest'] - date_range['earliest']).days + 1

    return create_api_success_response({
        'earliest_date': date_range['earliest'].strftime('%Y-%m-%d'),
        'latest_date': date_range['latest'].strftime('%Y-%m-%d'),
        'earliest_display': date_range['earliest'].strftime('%B %d, %Y'),
        'latest_display': date_range['latest'].strftime('%B %d, %Y'),
        'total_days': total_days
    })

@api_bp.route('/cache-status')
@handle_api_errors
def cache_status():
    """Get current cache status for monitoring."""
    try:
        status = current_app.weather_service.get_cache_status()
        return create_api_success_response(status)
    except Exception as e:
        return create_api_error_response(str(e), 500)


def _format_precipitation_response(per_station_data, sites):
    """Convert precipitation dataclass objects to JSON-serializable dicts."""
    stations_response = {}
    
    for station_id, data_points in per_station_data.items():
        site = next((s for s in sites if s['id'] == station_id), None)
        if not site:
            continue

        data_list = [
            {
                'label': point.label,
                'y': point.y,
                'intensity': point.intensity,
                'day': point.day,
                'timestamp': point.timestamp,
                'count': point.count,
                'show_label': point.show_label
            }
            for point in data_points
        ]

        stations_response[station_id] = {
            'name': site['name'],
            'data': data_list
        }

    return stations_response


def _format_water_level_response(per_station_data, sites, service):
    """Convert water level dataclass objects to JSON-serializable dicts."""
    stations_response = {}
    
    for station_id, data_points in per_station_data.items():
        site = next((s for s in sites if s['id'] == station_id), None)
        if not site:
            continue

        data_list = [
            {
                'label': point.label,
                'y': point.y,
                'alert_level': point.alert_level,
                'day': point.day,
                'timestamp': point.timestamp,
                'count': point.count,
                'show_label': point.show_label
            }
            for point in data_points
        ]

        stats = service.get_summary_statistics(data_points)

        stations_response[station_id] = {
            'name': site['name'],
            'data': data_list,
            'statistics': stats
        }

    return stations_response