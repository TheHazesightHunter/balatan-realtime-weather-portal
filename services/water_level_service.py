# Water Level Data Processing Service - Flood monitoring

import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Chart configuration constants
START_HOUR = 0
END_HOUR = 23
DATA_INTERVAL_HOURS = 1
LABEL_INTERVAL_HOURS = 2

# Data validation constants
MIN_VALID_WATER_LEVEL = 0.0
MAX_VALID_WATER_LEVEL = 15.0


@dataclass
class WaterLevelDataPoint:
    """Single water level data point for chart."""
    label: str
    y: float
    alert_level: str
    day: str
    timestamp: str
    count: int
    show_label: bool


class WaterLevelService:
    """Service for processing and analyzing water level data."""

    def __init__(self, metrics_service):
        """Initialize water level service with metrics service dependency."""
        self.metrics_service = metrics_service

    def get_24hour_intervals_per_station(
        self,
        weather_data: List[Dict],
        sites: List[Dict],
        target_date: Optional[datetime] = None
    ) -> Dict[str, List[WaterLevelDataPoint]]:
        """Process weather data into hourly water level intervals, separated by station."""
        # Determine target date
        if target_date:
            display_date = target_date
            logger.info("Getting hourly water level data for: %s", target_date.date())
        else:
            if not weather_data:
                display_date = datetime.now()
                logger.warning("No weather data available, using system date")
            else:
                latest_timestamp = None
                for reading in weather_data:
                    timestamp_str = reading.get('DateTime') or reading.get('DateTimeStamp', '')
                    parsed = self._parse_timestamp(timestamp_str)
                    if parsed:
                        if latest_timestamp is None or parsed > latest_timestamp:
                            latest_timestamp = parsed

                if latest_timestamp:
                    display_date = latest_timestamp
                    logger.info("Using latest data timestamp: %s", display_date)
                else:
                    display_date = datetime.now()
                    logger.warning("No valid timestamps found, using system date")

        # Time range: 12 AM to 11 PM
        start_time = display_date.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
        end_time = display_date.replace(hour=END_HOUR, minute=0, second=0, microsecond=0)

        logger.info("Generating hourly water level data from %s to %s",
                   start_time.strftime('%Y-%m-%d %I %p'),
                   end_time.strftime('%Y-%m-%d %I %p'))

        # Create hourly intervals
        intervals = self._create_hourly_intervals(start_time, end_time)
        logger.info("Created %d hourly intervals", len(intervals))

        # Group readings by station and interval
        station_interval_data = self._group_readings_by_station_and_interval(
            weather_data, intervals, start_time, end_time, display_date
        )

        # Format output for each station
        result = {}
        for site in sites:
            station_id = site['id']
            station_data = station_interval_data.get(station_id, {})

            formatted_data = self._format_interval_data_with_labels(
                intervals, station_data, display_date
            )
            result[station_id] = formatted_data

        logger.info("Generated %d hourly data points for %d stations",
                   len(intervals), len(result))
        return result

    def _create_hourly_intervals(self, start_time: datetime, end_time: datetime) -> List[datetime]:
        """Create hourly intervals from 12 AM to 11 PM."""
        intervals = []
        current = start_time

        while current <= end_time:
            intervals.append(current)
            current = current + timedelta(hours=DATA_INTERVAL_HOURS)

        logger.info("Generated %d hourly intervals: %s to %s",
                   len(intervals), intervals[0], intervals[-1])
        return intervals

    def _group_readings_by_station_and_interval(
        self,
        weather_data: List[Dict],
        intervals: List[datetime],
        start_time: datetime,
        end_time: datetime,
        display_date: datetime
    ) -> Dict[str, Dict[datetime, List[float]]]:
        """Group weather readings by both station and hourly time interval."""
        station_data = defaultdict(lambda: defaultdict(list))

        logger.info("Processing %d readings for date %s",
                   len(weather_data), display_date.date())

        for reading in weather_data:
            try:
                # Parse timestamp
                timestamp_str = reading.get('DateTime') or reading.get('DateTimeStamp', '')
                parsed_time = self._parse_timestamp(timestamp_str)

                if not parsed_time:
                    continue

                # Check if reading is within our time range
                if not (start_time <= parsed_time <= end_time + timedelta(hours=1)):
                    continue

                # Get station ID and water level
                station_id = reading.get('StationID')
                water_level = reading.get('WaterLevel')

                if not station_id or water_level is None:
                    continue

                # Convert water level to float and validate
                try:
                    water_level_float = float(water_level)
                    if not (MIN_VALID_WATER_LEVEL <= water_level_float <= MAX_VALID_WATER_LEVEL):
                        continue
                except (ValueError, TypeError):
                    continue

                # Find matching interval
                for interval_time in intervals:
                    next_interval = interval_time + timedelta(hours=1)
                    if interval_time <= parsed_time < next_interval:
                        station_data[station_id][interval_time].append(water_level_float)
                        break

            except (KeyError, AttributeError) as e:
                logger.warning("Error processing reading: %s", e)
                continue

        logger.info("Grouped data for %d stations into hourly intervals", len(station_data))
        return station_data

    def _format_interval_data_with_labels(
        self,
        intervals: List[datetime],
        interval_data: Dict[datetime, List[float]],
        display_date: datetime
    ) -> List[WaterLevelDataPoint]:
        """Format interval data with smart labeling."""
        result = []

        for interval_time in intervals:
            water_level_values = interval_data.get(interval_time, [])

            # Calculate average, or 0 if no data
            avg_water_level = (sum(water_level_values) / len(water_level_values)
                             if water_level_values else 0)

            # Classify alert level using MetricsService
            alert_level = self.metrics_service.get_alert_level(avg_water_level)

            # Format label
            label = self._format_time_label(interval_time)
            day_label = self._get_day_label(interval_time, display_date)

            # Determine if this hour should show label on X-axis
            show_label = (interval_time.hour % LABEL_INTERVAL_HOURS == 0)

            result.append(WaterLevelDataPoint(
                label=label,
                y=round(avg_water_level, 2),
                alert_level=alert_level,
                day=day_label,
                timestamp=interval_time.isoformat(),
                count=len(water_level_values),
                show_label=show_label
            ))

        return result

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None

        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        try:
            clean_str = timestamp_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_str)
            return dt.replace(tzinfo=None)
        except ValueError:
            pass

        logger.warning("Could not parse timestamp: %s", timestamp_str)
        return None

    def _format_time_label(self, dt: datetime) -> str:
        """Format datetime as readable time label."""
        hour = dt.hour
        if hour == 0:
            return "12 AM"
        elif hour < 12:
            return f"{hour} AM"
        elif hour == 12:
            return "12 PM"
        else:
            return f"{hour - 12} PM"

    def _get_day_label(self, dt: datetime, display_date: datetime) -> str:
        """Get day label relative to display date."""
        if dt.date() == display_date.date():
            return "Today"
        elif dt.date() < display_date.date():
            return "Yesterday"
        else:
            return "Tomorrow"

    def get_summary_statistics(self, data_points: List[WaterLevelDataPoint]) -> Dict:
        """Calculate summary statistics for water level data."""
        if not data_points:
            return {
                'average_level': 0,
                'max_level': 0,
                'min_level': 0,
                'highest_alert_level': 'normal',
                'critical_intervals': 0,
                'warning_intervals': 0,
                'alert_intervals': 0,
                'total_intervals': 0
            }

        water_levels = [point.y for point in data_points]
        alert_counts = {'critical': 0, 'warning': 0, 'alert': 0, 'advisory': 0, 'normal': 0}

        for point in data_points:
            alert_counts[point.alert_level] += 1

        # Determine highest alert level
        highest_alert = 'normal'
        for level in ['critical', 'warning', 'alert', 'advisory']:
            if alert_counts[level] > 0:
                highest_alert = level
                break

        return {
            'average_level': round(sum(water_levels) / len(water_levels), 2),
            'max_level': max(water_levels),
            'min_level': min(water_levels),
            'highest_alert_level': highest_alert,
            'critical_intervals': alert_counts['critical'],
            'warning_intervals': alert_counts['warning'],
            'alert_intervals': alert_counts['alert'],
            'total_intervals': len(data_points)
        }

    def get_available_date_range(self, weather_data: List[Dict]) -> Optional[Dict]:
        """Get the range of dates available in the weather data."""
        if not weather_data:
            return None

        valid_dates = []

        for reading in weather_data:
            timestamp_str = reading.get('DateTime') or reading.get('DateTimeStamp', '')
            parsed_time = self._parse_timestamp(timestamp_str)

            if parsed_time:
                valid_dates.append(parsed_time)

        if not valid_dates:
            logger.warning("No valid timestamps found in weather data")
            return None

        earliest = min(valid_dates)
        latest = max(valid_dates)

        logger.info("Date range available: %s to %s", earliest.date(), latest.date())

        return {
            'earliest': earliest,
            'latest': latest
        }