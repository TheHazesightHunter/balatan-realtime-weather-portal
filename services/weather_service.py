"""Weather Service - Handles API calls with caching and graceful fallback."""

import requests
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class WeatherCache:
    """Thread-safe cache for weather data with TTL and fallback support."""
    
    def __init__(self, ttl_seconds: int = 60, stale_ttl_seconds: int = 300):
        self._data: Optional[List[Dict]] = None
        self._last_fetch: Optional[datetime] = None
        self._last_success: Optional[datetime] = None
        self._ttl = timedelta(seconds=ttl_seconds)
        self._stale_ttl = timedelta(seconds=stale_ttl_seconds)
        self._lock = threading.Lock()
        self._fetch_errors = 0
        self._max_errors_before_backoff = 3
        self._backoff_until: Optional[datetime] = None
    
    def get(self) -> tuple[Optional[List[Dict]], bool, Optional[datetime]]:
        """
        Get cached data.
        Returns: (data, is_fresh, last_success_time)
        """
        with self._lock:
            if self._data is None:
                return None, False, None
            
            now = datetime.now()
            is_fresh = self._last_fetch and (now - self._last_fetch) < self._ttl
            
            return self._data, is_fresh, self._last_success
    
    def set(self, data: List[Dict], success: bool = True):
        """Store data in cache."""
        with self._lock:
            now = datetime.now()
            self._data = data
            self._last_fetch = now
            
            if success and data:
                self._last_success = now
                self._fetch_errors = 0
                self._backoff_until = None
    
    def record_error(self):
        """Record a fetch error for backoff calculation."""
        with self._lock:
            self._fetch_errors += 1
            if self._fetch_errors >= self._max_errors_before_backoff:
                backoff_seconds = min(60 * (2 ** (self._fetch_errors - self._max_errors_before_backoff)), 300)
                self._backoff_until = datetime.now() + timedelta(seconds=backoff_seconds)
                logger.warning(f"API errors exceeded threshold. Backing off for {backoff_seconds}s")
    
    def should_fetch(self) -> bool:
        """Check if we should attempt a new fetch."""
        with self._lock:
            now = datetime.now()
            
            if self._backoff_until and now < self._backoff_until:
                return False
            
            if self._last_fetch is None:
                return True
            
            return (now - self._last_fetch) >= self._ttl
    
    def get_stale_data(self) -> Optional[List[Dict]]:
        """Get data even if stale (for fallback scenarios)."""
        with self._lock:
            if self._data is None:
                return None
            
            now = datetime.now()
            if self._last_success and (now - self._last_success) < self._stale_ttl:
                return self._data
            
            return self._data
    
    def get_cache_status(self) -> Dict:
        """Get cache status for debugging/monitoring."""
        with self._lock:
            now = datetime.now()
            age_seconds = (now - self._last_fetch).total_seconds() if self._last_fetch else None
            
            return {
                'has_data': self._data is not None,
                'data_count': len(self._data) if self._data else 0,
                'age_seconds': age_seconds,
                'last_success': self._last_success.isoformat() if self._last_success else None,
                'fetch_errors': self._fetch_errors,
                'in_backoff': self._backoff_until and now < self._backoff_until
            }


class WeatherService:
    """Service for fetching and processing weather data with intelligent caching."""
    
    _cache = WeatherCache(ttl_seconds=60, stale_ttl_seconds=300)
    
    def __init__(self, api_url: str, timeout: int = 10):
        self.api_url = api_url
        self.timeout = timeout
        logger.info(f"WeatherService initialized with API: {api_url}")
    
    def _sanitize_reading(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """Convert string values to proper types and handle invalid data."""
        float_fields = [
            'WaterLevel', 'HourlyRain', 'WindSpeed', 'Temperature', 
            'Humidity', 'Pressure', 'HeatIndex', 'DailyRain'
        ]
        critical_fields = ['WaterLevel', 'HourlyRain']
        
        for field in float_fields:
            if field in reading and reading[field] is not None:
                try:
                    reading[field] = float(reading[field])
                except (ValueError, TypeError):
                    if field in critical_fields:
                        reading[field] = None
                    else:
                        reading[field] = 0.0
        
        if 'WindDirection' in reading:
            wind_dir = reading['WindDirection']
            if wind_dir is not None:
                reading['WindDirection'] = str(wind_dir).strip().upper()
        
        return reading
    
    def _fetch_from_api(self) -> Optional[List[Dict[str, Any]]]:
        """Internal method to fetch fresh data from external API."""
        try:
            logger.debug(f"Fetching weather data from {self.api_url}")
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, dict) and 'data' in data:
                data = data['data']
            
            if not isinstance(data, list):
                logger.error(f"Expected list, got {type(data)}")
                return None
            
            sanitized_data = [self._sanitize_reading(reading) for reading in data]
            logger.info(f"Successfully fetched {len(sanitized_data)} weather readings")
            return sanitized_data
            
        except requests.exceptions.Timeout:
            logger.warning(f"API request timed out after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"API request failed: {str(e)}")
            return None
        except ValueError as e:
            logger.warning(f"Invalid JSON response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return None
    
    def fetch_weather_data(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch weather data with intelligent caching.
        Returns cached data if fresh, otherwise fetches new data.
        Falls back to stale data if API fails.
        """
        cached_data, is_fresh, last_success = self._cache.get()
        
        if is_fresh and not force_refresh:
            logger.debug("Returning fresh cached data")
            return cached_data
        
        if not self._cache.should_fetch() and not force_refresh:
            if cached_data:
                logger.debug("In backoff period, returning cached data")
                return cached_data
        
        fresh_data = self._fetch_from_api()
        
        if fresh_data:
            self._cache.set(fresh_data, success=True)
            return fresh_data
        
        self._cache.record_error()
        
        stale_data = self._cache.get_stale_data()
        if stale_data:
            logger.info("API failed, returning stale cached data")
            return stale_data
        
        logger.error("No cached data available and API failed")
        return []
    
    def get_cache_status(self) -> Dict:
        """Get current cache status for monitoring."""
        return self._cache.get_cache_status()
    
    def get_latest_per_station(self, weather_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Get latest reading per station."""
        stations = {}
        
        station_id_map = {
            'St1': ['St1'],  
            'St2': ['St2'],  
            'St3': ['St3'],    
            'St4': ['St4'],         
            'St5': ['St5']           
        }
        
        for canonical_id, possible_ids in station_id_map.items():
            station_readings = []
            
            for reading in weather_data:
                api_station_id = reading.get('StationID')
                if api_station_id in possible_ids:
                    station_readings.append(reading)
            
            if station_readings:
                try:
                    station_readings.sort(
                        key=lambda x: x.get('Timestamp') or x.get('DateTime') or x.get('DateTimeStamp') or '', 
                        reverse=True
                    )
                    stations[canonical_id] = station_readings[0]
                except Exception as e:
                    logger.error(f"Error sorting readings for {canonical_id}: {e}")
                    stations[canonical_id] = station_readings[0]
        
        return stations
    
    def filter_by_station(self, weather_data: List[Dict], station_id: str) -> List[Dict]:
        """Filter weather data by station ID."""
        filtered = [r for r in weather_data if r.get('StationID') == station_id]
        
        try:
            sorted_data = sorted(
                filtered,
                key=lambda x: datetime.fromisoformat(
                    (x.get('Timestamp') or x.get('DateTimeStamp') or x.get('DateTime') or '').replace('Z', '+00:00')
                ),
                reverse=True
            )
            return sorted_data
        except (KeyError, ValueError, AttributeError):
            return filtered
    
    def get_latest_reading(self, weather_data: List[Dict]) -> Optional[Dict]:
        """Get the most recent weather reading from any station."""
        if not weather_data:
            return None
        
        try:
            latest = max(
                weather_data,
                key=lambda x: datetime.fromisoformat(
                    (x.get('Timestamp') or x.get('DateTimeStamp') or x.get('DateTime') or '').replace('Z', '+00:00')
                )
            )
            return latest
        except (ValueError, AttributeError):
            return weather_data[0] if weather_data else None
    
    def get_mdrrmo_latest_reading(self, weather_data: List[Dict]) -> Optional[Dict]:
        """Get latest reading from MDRRMO station."""
        mdrrmo_data = self.filter_by_station(weather_data, 'St1')
        return self.get_latest_reading(mdrrmo_data) if mdrrmo_data else None
    
    def get_24hour_average(self, weather_data: List[Dict]) -> Dict[str, Optional[float]]:
        """Calculate 24-hour averages for all metrics."""
        if not weather_data:
            return {
                'avg_temperature': None,
                'avg_humidity': None,
                'avg_pressure': None,
                'avg_wind_speed': None,
                'total_rainfall': None
            }
        
        temps, humidity, pressure, wind_speed, rainfall = [], [], [], [], []
        
        for reading in weather_data[:24]:
            if reading.get('Temperature') is not None:
                temps.append(reading['Temperature'])
            if reading.get('Humidity') is not None:
                humidity.append(reading['Humidity'])
            if reading.get('Pressure') is not None:
                pressure.append(reading['Pressure'])
            if reading.get('WindSpeed') is not None:
                wind_speed.append(reading['WindSpeed'])
            if reading.get('HourlyRain') is not None:
                rainfall.append(reading['HourlyRain'])
        
        return {
            'avg_temperature': sum(temps) / len(temps) if temps else None,
            'avg_humidity': sum(humidity) / len(humidity) if humidity else None,
            'avg_pressure': sum(pressure) / len(pressure) if pressure else None,
            'avg_wind_speed': sum(wind_speed) / len(wind_speed) if wind_speed else None,
            'total_rainfall': sum(rainfall) if rainfall else None
        }

    def generate_weather_alert(self, latest_reading: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Generate weather alert using config color system."""
        from config import UIColorSystem, AlertLevelConfig, WeatherThresholds
        
        if not latest_reading:
            return {
                'level': 'no-data',
                'message': 'Connecting to weather sensors...',
                'color': UIColorSystem.ALERT_NORMAL
            }
        
        try:
            rainfall = float(latest_reading.get('HourlyRain') or 0)
            water_level = float(latest_reading.get('WaterLevel') or 0)
        except (ValueError, TypeError):
            rainfall, water_level = 0.0, 0.0
        
        if water_level >= WeatherThresholds.WATER_CRITICAL:
            config = AlertLevelConfig.get_config('critical')
            return {
                'level': 'critical',
                'message': f'CRITICAL: Water level at {water_level:.1f}cm - Immediate evacuation required',
                'color': config['color']
            }
        elif water_level >= WeatherThresholds.WATER_WARNING:
            config = AlertLevelConfig.get_config('warning')
            return {
                'level': 'warning',
                'message': f'WARNING: Water level at {water_level:.1f}cm - Prepare for evacuation',
                'color': config['color']
            }
        elif water_level >= WeatherThresholds.WATER_ALERT:
            config = AlertLevelConfig.get_config('alert')
            return {
                'level': 'alert',
                'message': f'ALERT: Water level at {water_level:.1f}cm - Monitor closely',
                'color': config['color']
            }
        elif water_level >= WeatherThresholds.WATER_ADVISORY:
            config = AlertLevelConfig.get_config('advisory')
            return {
                'level': 'advisory',
                'message': f'ADVISORY: Water level at {water_level:.1f}cm - Stay informed',
                'color': config['color']
            }
        
        if rainfall >= WeatherThresholds.RAINFALL_HEAVY:
            config = AlertLevelConfig.get_config('warning')
            return {
                'level': 'warning',
                'message': f'Heavy rainfall detected: {rainfall:.1f}mm/hr - Monitor water levels',
                'color': config['color']
            }
        elif rainfall >= WeatherThresholds.RAINFALL_MODERATE:
            config = AlertLevelConfig.get_config('advisory')
            return {
                'level': 'advisory',
                'message': f'Moderate rainfall: {rainfall:.1f}mm/hr - Stay alert',
                'color': config['color']
            }
        
        config = AlertLevelConfig.get_config('normal')
        return {
            'level': 'normal',
            'message': 'Weather conditions normal - All systems operational',
            'color': config['color']
        }
    