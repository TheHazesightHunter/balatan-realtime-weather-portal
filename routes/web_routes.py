"""Web routes for page rendering."""

from flask import Blueprint, render_template, current_app
from config import MetricCardConfig
from utils.error_handlers import handle_service_errors

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
@handle_service_errors
def home():
    """Render home dashboard with weather metrics and alerts."""
    weather_data = current_app.weather_service.fetch_weather_data()
    stations = current_app.weather_service.get_latest_per_station(weather_data)
    
    latest = stations.get('St4')
    
    if not latest:
        latest = current_app.weather_service.get_mdrrmo_latest_reading(weather_data)
    
    if not latest:
        latest = current_app.weather_service.get_latest_reading(weather_data)
        current_app.logger.warning("No MDRRMO data found, using fallback station")
    
    weather_alert = current_app.weather_service.generate_weather_alert(latest)
    
    metrics = current_app.metrics_service.calculate_dashboard_metrics(stations)

    return render_template('home.html',
        weather=weather_data,
        latest=latest,
        weather_alert=weather_alert,
        metrics=metrics,
        card_config=MetricCardConfig.CARDS
    )


@web_bp.route('/sites/<site_id>')
@handle_service_errors  
def site_detail(site_id):
    """Render detailed view for a specific monitoring site."""
    site = next((s for s in current_app.config['SITES'] if s['id'] == site_id), None)
    if not site:
        return render_template('errors/404.html'), 404

    weather_data = current_app.weather_service.fetch_weather_data()
    site_weather = current_app.weather_service.filter_by_station(weather_data, site_id)
    
    # Get latest reading for current station
    if site_id == 'St1':
        latest = current_app.weather_service.get_mdrrmo_latest_reading(weather_data)
    else:
        latest = current_app.weather_service.get_latest_reading(site_weather)
    
    # Get latest readings for ALL stations (for "Other Stations" sidebar)
    all_stations_latest = current_app.weather_service.get_latest_per_station(weather_data)
    
    weather_alert = current_app.weather_service.generate_weather_alert(latest)

    return render_template('sites/site_detail.html',
        site=site,
        latest=latest,
        weather_alert=weather_alert,
        weather=site_weather[:24],
        current_site_id=site_id,
        all_stations_latest=all_stations_latest
    )


@web_bp.route('/precipitation')
@handle_service_errors
def precipitation():
    """Render precipitation analysis page."""
    return render_template('precipitation.html')


@web_bp.route('/water-level')
@handle_service_errors
def water_level():
    """Render water level monitoring page."""
    return render_template('water_level.html')


@web_bp.route('/about')
def about():
    """Render about page."""
    return render_template('about.html')


@web_bp.route('/contact')
def contact():
    """Render contact page."""
    return render_template('contact.html')