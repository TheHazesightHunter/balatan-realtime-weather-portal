"""Metrics Service - Dashboard metrics, alerts, and station status."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from config import WeatherThresholds, AlertLevelConfig, RainfallForecastConfig

STATION_OFFLINE_THRESHOLD_MINUTES = 60
TOTAL_STATIONS = 5


@dataclass
class RainfallForecast:
    level: str
    icon: str
    color: str


@dataclass  
class AlertLevelInfo:
    level: str
    icon: str
    color: str
    description: str


@dataclass
class StationAlert:
    station_id: str
    station_name: str
    alert_level: str
    water_level: float
    is_online: bool
    last_update: Optional[datetime]


@dataclass
class DashboardMetrics:
    highest_alert_level: str
    highest_alert_count: int
    critical_count: int
    warning_count: int
    alert_count: int
    advisory_count: int
    attention_stations: List[str]
    online_sensors: int
    total_sensors: int
    offline_stations: List[str]
    rainfall_forecast: RainfallForecast
    alert_level_info: AlertLevelInfo
    station_alerts: List[StationAlert]


class MetricsService:
    
    def __init__(self, sites: List[Dict] = None):
        self.sites = sites or []
        self.total_sensors = TOTAL_STATIONS
    
    def _to_float(self, value: Union[str, float, int, None]) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    def _parse_timestamp(self, data: Dict) -> Optional[datetime]:
        timestamp_str = data.get('DateTime') or data.get('DateTimeStamp') or data.get('Timestamp')
        
        if not timestamp_str:
            return None
        
        try:
            if isinstance(timestamp_str, datetime):
                return timestamp_str
            
            ts = str(timestamp_str).replace('Z', '+00:00')
            clean_ts = ts.split('+')[0].split('.')[0]
            
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(clean_ts, fmt)
                except ValueError:
                    continue
            
            return datetime.fromisoformat(ts.replace('Z', ''))
        except (ValueError, AttributeError):
            return None
    
    def _is_station_online(self, data: Dict) -> bool:
        if not data:
            return False
        
        timestamp = self._parse_timestamp(data)
        if not timestamp:
            return False
        
        now = datetime.now()
        if timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=None)
        
        age = now - timestamp
        return age <= timedelta(minutes=STATION_OFFLINE_THRESHOLD_MINUTES)
    
    def _get_station_name(self, station_id: str) -> str:
        for site in self.sites:
            if site['id'] == station_id:
                return site['name']
        return station_id
    
    def get_alert_level(self, water_level: Union[str, float, int, None]) -> str:
        level = self._to_float(water_level)
        
        if level is None:
            return 'normal'
        
        if level >= WeatherThresholds.WATER_CRITICAL:
            return 'critical'
        elif level >= WeatherThresholds.WATER_WARNING:
            return 'warning'
        elif level >= WeatherThresholds.WATER_ALERT:
            return 'alert'
        elif level >= WeatherThresholds.WATER_ADVISORY:
            return 'advisory'
        return 'normal'
    
    def get_rainfall_level(self, rainfall: Union[str, float, int, None]) -> str:
        level = self._to_float(rainfall)
        
        if level is None:
            return 'no_data'
        
        if level >= WeatherThresholds.RAINFALL_HEAVY:
            return 'heavy'
        elif level >= WeatherThresholds.RAINFALL_MODERATE:
            return 'moderate'
        elif level >= WeatherThresholds.RAINFALL_LIGHT:
            return 'light'
        return 'none'
    
    def calculate_dashboard_metrics(self, station_data: Dict[str, Dict]) -> DashboardMetrics:
        alert_counts = {'critical': 0, 'warning': 0, 'alert': 0, 'advisory': 0, 'normal': 0}
        attention_stations = []
        offline_stations = []
        station_alerts = []
        online_count = 0
        total_rainfall = 0.0
        rainfall_readings = 0
        
        for station_id, data in station_data.items():
            station_name = self._get_station_name(station_id)
            
            if not data:
                offline_stations.append(station_name)
                continue
            
            is_online = self._is_station_online(data)
            
            if is_online:
                online_count += 1
            else:
                offline_stations.append(station_name)
            
            water_level = self._to_float(data.get('WaterLevel'))
            alert_level = self.get_alert_level(water_level)
            alert_counts[alert_level] += 1
            
            station_alert = StationAlert(
                station_id=station_id,
                station_name=station_name,
                alert_level=alert_level,
                water_level=water_level or 0.0,
                is_online=is_online,
                last_update=self._parse_timestamp(data)
            )
            station_alerts.append(station_alert)
            
            if alert_level in ['critical', 'warning', 'alert']:
                attention_stations.append(station_name)
            
            rainfall = self._to_float(data.get('HourlyRain'))
            if rainfall is not None:
                total_rainfall += rainfall
                rainfall_readings += 1
        
        highest_alert_level = 'normal'
        highest_alert_count = 0
        
        for level in ['critical', 'warning', 'alert', 'advisory']:
            if alert_counts[level] > 0:
                highest_alert_level = level
                highest_alert_count = alert_counts[level]
                break
        
        avg_rainfall = total_rainfall / rainfall_readings if rainfall_readings > 0 else 0
        rainfall_forecast = self._get_rainfall_forecast(avg_rainfall)
        alert_level_info = self._get_alert_level_info(highest_alert_level)
        
        return DashboardMetrics(
            highest_alert_level=highest_alert_level,
            highest_alert_count=highest_alert_count,
            critical_count=alert_counts['critical'],
            warning_count=alert_counts['warning'],
            alert_count=alert_counts['alert'],
            advisory_count=alert_counts['advisory'],
            attention_stations=attention_stations,
            online_sensors=online_count,
            total_sensors=self.total_sensors,
            offline_stations=offline_stations,
            rainfall_forecast=rainfall_forecast,
            alert_level_info=alert_level_info,
            station_alerts=station_alerts
        )
    
    def _get_rainfall_forecast(self, avg_rainfall: float) -> RainfallForecast:
        rainfall_level = self.get_rainfall_level(avg_rainfall)
        config = RainfallForecastConfig.get_config(rainfall_level)
        
        return RainfallForecast(
            level=config['level'],
            icon=config['icon'],
            color=config['color']
        )
    
    def _get_alert_level_info(self, alert_level: str) -> AlertLevelInfo:
        config = AlertLevelConfig.get_config(alert_level)
        
        return AlertLevelInfo(
            level=config['level'],
            icon=config['icon'],
            color=config['color'],
            description=config['description']
        )
    
    def get_station_status(self, station_data: Dict) -> Dict:
        if not station_data:
            return {
                'alert_level': 'normal',
                'rainfall_level': 'no_data',
                'water_level': None,
                'rainfall': None,
                'is_online': False,
                'needs_attention': False
            }
        
        water_level = self._to_float(station_data.get('WaterLevel'))
        rainfall = self._to_float(station_data.get('HourlyRain'))
        alert_level = self.get_alert_level(water_level)
        
        return {
            'alert_level': alert_level,
            'rainfall_level': self.get_rainfall_level(rainfall),
            'water_level': water_level,
            'rainfall': rainfall,
            'is_online': self._is_station_online(station_data),
            'needs_attention': alert_level in ['critical', 'warning', 'alert']
        }