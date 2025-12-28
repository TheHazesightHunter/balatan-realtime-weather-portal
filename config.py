"""Application configuration"""

import os

class UIColorSystem:
    
    PRIMARY = '#409ac7'
    SECONDARY = '#64748b'
    
    TEXT_PRIMARY = '#1a202c'
    TEXT_SECONDARY = '#64748b'
    TEXT_MUTED = '#9ca3af'
    
    WHITE = '#ffffff'
    BACKGROUND_LIGHT = '#f8fafc'
    BACKGROUND_DARK = '#1a202c'
    
    BORDER_LIGHT = '#e2e8f0'
    BORDER_MEDIUM = '#cbd5e0'
    
    SUCCESS = '#10b981'
    WARNING = '#f59e0b'
    ERROR = '#ef4444'
    INFO = '#3b82f6'
    
    PRIMARY_LIGHT = '#eff3f9'
    BLACK = '#0c0c0d'
    LIGHT_BLACK = '#141516'
    LIGHTEST_GRAY = '#eaeaec'
    LIGHT_GRAY = '#92949f'
    DARK_GRAY = '#45474f'
    
    ALERT_NORMAL = PRIMARY
    ALERT_ADVISORY = PRIMARY
    ALERT_ALERT = '#ffbe0b'
    ALERT_WARNING = '#fb8500'
    ALERT_CRITICAL = '#ff006e'
    
    FLOOD_NORMAL = SUCCESS
    FLOOD_ADVISORY = '#0ea5e9'
    FLOOD_ALERT = '#eab308'
    FLOOD_WARNING = '#f59e0b'
    FLOOD_CRITICAL = '#dc2626'
    
    STATION_COLORS = {
        'St1': PRIMARY,
        'St2': '#8b5cf6',
        'St3': '#ec4899',
        'St4': '#6366f1',
        'St5': '#06b6d4',
    }


class ColorAPI:
    """API layer for color management."""
    
    @staticmethod
    def get_css_variables():
        """Generate CSS custom properties for frontend consumption."""
        return {
            '--color-primary': UIColorSystem.PRIMARY,
            '--color-secondary': UIColorSystem.SECONDARY,
            '--color-white': UIColorSystem.WHITE,
            '--color-black': UIColorSystem.BLACK,
            '--color-light-black': UIColorSystem.LIGHT_BLACK,
            '--color-lightest-gray': UIColorSystem.LIGHTEST_GRAY,
            '--color-light-gray': UIColorSystem.LIGHT_GRAY,
            '--color-dark-gray': UIColorSystem.DARK_GRAY,
            '--color-text-primary': UIColorSystem.TEXT_PRIMARY,
            '--color-text-secondary': UIColorSystem.TEXT_SECONDARY,
            '--color-text-muted': UIColorSystem.TEXT_MUTED,
            '--color-background-light': UIColorSystem.BACKGROUND_LIGHT,
            '--color-border-light': UIColorSystem.BORDER_LIGHT,
            '--color-border-medium': UIColorSystem.BORDER_MEDIUM,
            '--alert-normal': UIColorSystem.ALERT_NORMAL,
            '--alert-advisory': UIColorSystem.ALERT_ADVISORY,
            '--alert-alert': UIColorSystem.ALERT_ALERT,
            '--alert-warning': UIColorSystem.ALERT_WARNING,
            '--alert-critical': UIColorSystem.ALERT_CRITICAL,
            '--flood-normal': UIColorSystem.FLOOD_NORMAL,
            '--flood-advisory': UIColorSystem.FLOOD_ADVISORY,
            '--flood-alert': UIColorSystem.FLOOD_ALERT,
            '--flood-warning': UIColorSystem.FLOOD_WARNING,
            '--flood-critical': UIColorSystem.FLOOD_CRITICAL,
            '--color-success': UIColorSystem.SUCCESS,
            '--color-info': UIColorSystem.INFO,
            '--color-warning': UIColorSystem.WARNING,
            '--color-error': UIColorSystem.ERROR,
            '--station-st1': UIColorSystem.STATION_COLORS['St1'],
            '--station-st2': UIColorSystem.STATION_COLORS['St2'],
            '--station-st3': UIColorSystem.STATION_COLORS['St3'],
            '--station-st4': UIColorSystem.STATION_COLORS['St4'],
            '--station-st5': UIColorSystem.STATION_COLORS['St5'],
        }
    
    @staticmethod
    def get_javascript_config():
        """Generate JavaScript color configuration."""
        return {
            'base_colors': {
                'primary': UIColorSystem.PRIMARY,
                'secondary': UIColorSystem.SECONDARY,
                'white': UIColorSystem.WHITE,
                'black': UIColorSystem.BLACK,
                'text_primary': UIColorSystem.TEXT_PRIMARY,
                'text_secondary': UIColorSystem.TEXT_SECONDARY,
                'text_muted': UIColorSystem.TEXT_MUTED,
                'success': UIColorSystem.SUCCESS,
                'warning': UIColorSystem.WARNING,
                'error': UIColorSystem.ERROR,
                'info': UIColorSystem.INFO
            },
            'alert_colors': {
                'normal': UIColorSystem.ALERT_NORMAL,
                'advisory': UIColorSystem.ALERT_ADVISORY,
                'alert': UIColorSystem.ALERT_ALERT,
                'warning': UIColorSystem.ALERT_WARNING,
                'critical': UIColorSystem.ALERT_CRITICAL
            },
            'flood_colors': {
                'normal': UIColorSystem.FLOOD_NORMAL,
                'advisory': UIColorSystem.FLOOD_ADVISORY,
                'alert': UIColorSystem.FLOOD_ALERT,
                'warning': UIColorSystem.FLOOD_WARNING,
                'critical': UIColorSystem.FLOOD_CRITICAL
            },
            'station_colors': UIColorSystem.STATION_COLORS
        }


class WeatherThresholds:
    """Weather monitoring thresholds based on PAGASA standards."""
    
    RAINFALL_HEAVY = 30.0
    RAINFALL_MODERATE = 15.0
    RAINFALL_LIGHT = 5.0
    
    WATER_CRITICAL = 1000.0
    WATER_WARNING = 900.0
    WATER_ALERT = 800.0
    WATER_ADVISORY = 700.0


class ChartConfig:
    """Chart styling and behavior configuration."""
    
    HEIGHTS = {
        'mobile_sm': 220,
        'mobile': 250,
        'tablet': 320,
        'desktop': 400
    }

    STYLING = {
        'labelFontColor': UIColorSystem.TEXT_SECONDARY,
        'lineColor': UIColorSystem.BORDER_LIGHT,
        'tickColor': UIColorSystem.BORDER_LIGHT,
        'gridColor': '#f1f5f9',
        'backgroundColor': UIColorSystem.WHITE,
        'titleFontColor': UIColorSystem.TEXT_PRIMARY,
    }

    ANIMATION_DURATION = 300
    TOOLTIP_DELAY = 100
    REFRESH_INTERVAL = 60000
    ICON_INTERVAL = 2
    ICON_SIZE = 36
    LABEL_INTERVAL = 2

    ARROW_SIZES = {
        'desktop': 40,
        'tablet': 32,
        'mobile': 28
    }


class AlertLevelConfig:
    """Alert configuration with colors, icons, and descriptions."""
    
    LEVELS = {
        'critical': {
            'level': 'Critical',
            'icon': 'fa-exclamation-triangle',
            'color': UIColorSystem.ALERT_CRITICAL,
            'description': 'Immediate evacuation required',
            'css_class': 'alert-critical'
        },
        'warning': {
            'level': 'Warning',
            'icon': 'fa-exclamation-circle',
            'color': UIColorSystem.ALERT_WARNING,
            'description': 'Prepare for evacuation',
            'css_class': 'alert-warning'
        },
        'alert': {
            'level': 'Alert',
            'icon': 'fa-bolt',
            'color': UIColorSystem.ALERT_ALERT,
            'description': 'Monitor situation closely',
            'css_class': 'alert-alert'
        },
        'advisory': {
            'level': 'Advisory',
            'icon': 'fa-info-circle',
            'color': UIColorSystem.ALERT_ADVISORY,
            'description': 'Stay informed',
            'css_class': 'alert-advisory'
        },
        'normal': {
            'level': 'Normal',
            'icon': 'fa-check-circle',
            'color': UIColorSystem.ALERT_NORMAL,
            'description': 'All systems normal',
            'css_class': 'alert-normal'
        }
    }

    @classmethod
    def get_config(cls, alert_level: str) -> dict:
        return cls.LEVELS.get(alert_level, cls.LEVELS['normal'])


class RainfallForecastConfig:
    """Rainfall forecast configuration."""
    
    LEVELS = {
        'heavy': {
            'level': 'Heavy Rain',
            'icon': 'fa-cloud-showers-heavy',
            'color': UIColorSystem.ALERT_CRITICAL,
            'description': 'Heavy rainfall expected'
        },
        'moderate': {
            'level': 'Moderate Rain',
            'icon': 'fa-cloud-rain',
            'color': UIColorSystem.ALERT_WARNING,
            'description': 'Moderate rainfall expected'
        },
        'light': {
            'level': 'Light Rain',
            'icon': 'fa-cloud-sun-rain',
            'color': UIColorSystem.ALERT_ADVISORY,
            'description': 'Light rainfall expected'
        },
        'none': {
            'level': 'Clear',
            'icon': 'fa-sun',
            'color': UIColorSystem.ALERT_NORMAL,
            'description': 'Clear weather conditions'
        },
        'no_data': {
            'level': 'No Data',
            'icon': 'fa-question-circle',
            'color': UIColorSystem.TEXT_MUTED,
            'description': 'Weather data unavailable'
        }
    }

    @classmethod
    def get_config(cls, rainfall_level: str) -> dict:
        return cls.LEVELS.get(rainfall_level, cls.LEVELS['no_data'])

class WeatherIconConfig:
    """Weather icon configuration based on rainfall and time of day."""
    
    # Rainfall thresholds for icon selection (mm/hr)
    RAINFALL_NONE = 0.0
    RAINFALL_LIGHT_MIN = 0.5
    RAINFALL_LIGHT_MAX = 5.0
    RAINFALL_MODERATE_MAX = 15.0
    # Above RAINFALL_MODERATE_MAX = heavy
    
    # Night hours: 18:00 (6 PM) to 04:59 (5 AM)
    NIGHT_START_HOUR = 18
    NIGHT_END_HOUR = 5
    
    # Icon filenames (stored in static/media/forecast-icons/)
    ICONS = {
        'day': {
            'clear': 'sunny.png',
            'light': 'light-rain.png',
            'moderate': 'rainy.png',
            'heavy': 'intense-rain.png'
        },
        'night': {
            'clear': 'night-no-rain.png',
            'light': 'night-rainy.png',
            'moderate': 'night-rainy.png',
            'heavy': 'night-rainy.png'
        }
    }
    
    @classmethod
    def is_night_time(cls, hour: int) -> bool:
        """Check if given hour is night time (18:00 to 04:59)."""
        return hour >= cls.NIGHT_START_HOUR or hour < cls.NIGHT_END_HOUR
    
    @classmethod
    def get_rainfall_category(cls, rainfall: float) -> str:
        """Get rainfall category based on mm/hr value."""
        if rainfall is None or rainfall < cls.RAINFALL_LIGHT_MIN:
            return 'clear'
        elif rainfall <= cls.RAINFALL_LIGHT_MAX:
            return 'light'
        elif rainfall <= cls.RAINFALL_MODERATE_MAX:
            return 'moderate'
        else:
            return 'heavy'
    
    @classmethod
    def get_icon(cls, rainfall: float, hour: int) -> str:
        """Get appropriate weather icon filename."""
        time_of_day = 'night' if cls.is_night_time(hour) else 'day'
        category = cls.get_rainfall_category(rainfall)
        return cls.ICONS[time_of_day][category]
    
    @classmethod
    def get_icon_path(cls, rainfall: float, hour: int) -> str:
        """Get full icon path for use in templates."""
        icon = cls.get_icon(rainfall, hour)
        return f'media/forecast-icons/{icon}'
    
    @classmethod
    def get_js_config(cls) -> dict:
        """Get configuration for JavaScript consumption."""
        return {
            'thresholds': {
                'none': cls.RAINFALL_NONE,
                'light_min': cls.RAINFALL_LIGHT_MIN,
                'light_max': cls.RAINFALL_LIGHT_MAX,
                'moderate_max': cls.RAINFALL_MODERATE_MAX
            },
            'night_hours': {
                'start': cls.NIGHT_START_HOUR,
                'end': cls.NIGHT_END_HOUR
            },
            'icons': cls.ICONS
        }

class MetricCardConfig:
    """Dashboard metric card configuration."""
    
    CARDS = {
        'alert_level': {
            'title': 'Highest Alert Level',
            'description': 'Current maximum alert level across all stations',
            'show_count': True
        },
        'rainfall_forecast': {
            'title': 'Rainfall Forecast',
            'description': 'Current rainfall intensity prediction',
            'show_icon': True,
            'show_color': True
        },
        'attention_stations': {
            'title': 'Stations Requiring Attention',
            'description': 'Number of stations with active alerts',
            'show_fraction': True,
            'icon': 'fas fa-exclamation-triangle'
        },
        'online_sensors': {
            'title': 'Weather Stations Online',
            'description': 'Number of sensors currently reporting data',
            'show_fraction': True,
            'icons': {
                'all_online': 'fas fa-check-circle text-success',
                'some_offline': 'fas fa-exclamation-triangle text-warning',
                'many_offline': 'fas fa-exclamation-circle text-danger'
            }
        }
    }

    @classmethod
    def get_card_config(cls, card_name: str) -> dict:
        return cls.CARDS.get(card_name, {})

    @classmethod
    def get_all_cards(cls) -> dict:
        return cls.CARDS


class APIConfig:
    """API endpoint and behavior configuration."""
    
    BASE_URL = 'https://apaw.cspc.edu.ph/apawbalatanapi/APIv1/Weather'
    TIMEOUT = 8
    RETRY_ATTEMPTS = 3

    ENDPOINTS = {
        'weather': '/api/weather-data',
        'precipitation': '/api/precipitation-data',
        'water_level': '/api/water-level-data',
        'stations': '/api/config/stations',
        'complete_config': '/api/config/complete',
        'css_variables': '/api/css-variables'
    }

    CACHE_DURATION = 300
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_PERIOD = 3600


class SystemConfig:
    """System-wide configuration."""
    
    MAX_RECORDS_PER_REQUEST = 1000
    DATABASE_POOL_SIZE = 10
    SESSION_LIFETIME = 3600
    CSRF_PROTECTION = True
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class SiteConfig:
    """Site and station configuration."""
    
    SITES = [
        {
            'id': 'St1',
            'name': 'Binudegahan Station',
            'location': {'lat': 13.3483, 'lng': 123.2609},
            'elevation': 14.7,
            'color': UIColorSystem.STATION_COLORS['St1']
        },
        {
            'id': 'St2',
            'name': 'Mangit Station',
            'location': {'lat': 13.3464, 'lng': 123.2517},
            'elevation': 10.5,
            'color': UIColorSystem.STATION_COLORS['St2']
        },
        {
            'id': 'St3',
            'name': 'Laganac Station',
            'location': {'lat': 13.3296, 'lng': 123.2481},
            'elevation': 18.1,
            'color': UIColorSystem.STATION_COLORS['St3']
        },
        {
            'id': 'St4',
            'name': 'MDRRMO Station',
            'location': {'lat': 13.31639, 'lng': 123.24003},
            'elevation': 15.2,
            'color': UIColorSystem.STATION_COLORS['St4']
        },
        {
            'id': 'St5',
            'name': 'Luluasan Station',
            'location': {'lat': 13.3235, 'lng': 123.2344},
            'elevation': 12.8,
            'color': UIColorSystem.STATION_COLORS['St5']
        }
    ]

class Config:
    """Base Flask configuration."""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    API_URL = APIConfig.BASE_URL
    API_TIMEOUT = APIConfig.TIMEOUT
    SITES = SiteConfig.SITES
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()


class TestingConfig(Config):
    """Testing environment configuration."""
    
    DEBUG = True
    TESTING = True
    API_TIMEOUT = 5


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_complete_config():
    """Get all configuration for frontend consumption."""
    return {
        'colors': {
            'primary': UIColorSystem.PRIMARY,
            'secondary': UIColorSystem.SECONDARY,
            'text_primary': UIColorSystem.TEXT_PRIMARY,
            'text_secondary': UIColorSystem.TEXT_SECONDARY,
            'text_muted': UIColorSystem.TEXT_MUTED,
            'white': UIColorSystem.WHITE,
            'background_light': UIColorSystem.BACKGROUND_LIGHT,
            'border_light': UIColorSystem.BORDER_LIGHT,
            'border_medium': UIColorSystem.BORDER_MEDIUM,
            'success': UIColorSystem.SUCCESS,
            'warning': UIColorSystem.WARNING,
            'error': UIColorSystem.ERROR,
            'info': UIColorSystem.INFO
        },
        'alert_colors': {
            'normal': UIColorSystem.ALERT_NORMAL,
            'advisory': UIColorSystem.ALERT_ADVISORY,
            'alert': UIColorSystem.ALERT_ALERT,
            'warning': UIColorSystem.ALERT_WARNING,
            'critical': UIColorSystem.ALERT_CRITICAL
        },
        'flood_colors': {
            'normal': UIColorSystem.FLOOD_NORMAL,
            'advisory': UIColorSystem.FLOOD_ADVISORY,
            'alert': UIColorSystem.FLOOD_ALERT,
            'warning': UIColorSystem.FLOOD_WARNING,
            'critical': UIColorSystem.FLOOD_CRITICAL
        },
        'station_colors': UIColorSystem.STATION_COLORS,
        'chart_styling': ChartConfig.STYLING,
        'chart_heights': ChartConfig.HEIGHTS,
        'chart_behavior': {
            'animation_duration': ChartConfig.ANIMATION_DURATION,
            'tooltip_delay': ChartConfig.TOOLTIP_DELAY,
            'refresh_interval': ChartConfig.REFRESH_INTERVAL,
            'icon_interval': ChartConfig.ICON_INTERVAL,
            'icon_size': ChartConfig.ICON_SIZE,
            'arrow_sizes': ChartConfig.ARROW_SIZES
        },
        'thresholds': {
            'rainfall_heavy': WeatherThresholds.RAINFALL_HEAVY,
            'rainfall_moderate': WeatherThresholds.RAINFALL_MODERATE,
            'rainfall_light': WeatherThresholds.RAINFALL_LIGHT,
            'water_level': {
                'critical': WeatherThresholds.WATER_CRITICAL,
                'warning': WeatherThresholds.WATER_WARNING,
                'alert': WeatherThresholds.WATER_ALERT,
                'advisory': WeatherThresholds.WATER_ADVISORY
            }
        },
        'alert_levels': AlertLevelConfig.LEVELS,
        'rainfall_levels': RainfallForecastConfig.LEVELS,
        'api_endpoints': APIConfig.ENDPOINTS,
        'sites': SiteConfig.SITES
    }


def get_template_context():
    """Get context for Jinja2 template injection."""
    return {
        'ui_colors': UIColorSystem,
        'station_colors': UIColorSystem.STATION_COLORS,
        'css_variables': ColorAPI.get_css_variables(),
        'alert_colors': {
            'normal': UIColorSystem.ALERT_NORMAL,
            'advisory': UIColorSystem.ALERT_ADVISORY,
            'alert': UIColorSystem.ALERT_ALERT,
            'warning': UIColorSystem.ALERT_WARNING,
            'critical': UIColorSystem.ALERT_CRITICAL
        },
        'flood_colors': {
            'normal': UIColorSystem.FLOOD_NORMAL,
            'advisory': UIColorSystem.FLOOD_ADVISORY,
            'alert': UIColorSystem.FLOOD_ALERT,
            'warning': UIColorSystem.FLOOD_WARNING,
            'critical': UIColorSystem.FLOOD_CRITICAL
        },
        'weather_icon_config': WeatherIconConfig.get_js_config()
    }