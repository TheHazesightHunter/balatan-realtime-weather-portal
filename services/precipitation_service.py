"""Precipitation Data Processing Service"""

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


@dataclass
class PrecipitationDataPoint:
    label: str
    y: float
    intensity: str
    day: str
    timestamp: str
    count: int
    show_label: bool


class PrecipitationService:

    def __init__(self, metrics_service):
        # Initialize precipitation service with metrics service dependency
        self.metrics_service = metrics_service

    def get_24hour_intervals_per_station(
        self,
        weather_data: List[Dict],
        sites: List[Dict],
        target_date: Optional[datetime] = None
    ) -> Dict[str, List[PrecipitationDataPoint]]:
        """Process weather data into hourly intervals, separated by station."""
        # Determine target date
        if target_date:
            display_date = target_date
            logger.info("Getting hourly data for: %s", target_date.date())
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

        # Time range: 12 AM to 11 PM of the target date
        start_time = display_date.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
        end_time = display_date.replace(hour=END_HOUR, minute=0, second=0, microsecond=0)

        logger.info("Generating hourly data from %s to %s",
                   start_time.strftime('%Y-%m-%d %I %p'),
                   end_time.strftime('%Y-%m-%d %I %p'))

        # Create hourly intervals (24 points: 12 AM, 1 AM, 2 AM... 11 PM)
        intervals = self._create_hourly_intervals(start_time, end_time)
        logger.info("Created %d hourly intervals", len(intervals))

        # Group readings by both station and interval
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

                # Get station ID and rainfall
                station_id = reading.get('StationID')
                rainfall = reading.get('HourlyRain')

                if not station_id or rainfall is None:
                    continue

                # Convert rainfall to float
                try:
                    rainfall_float = float(rainfall)
                    if rainfall_float < 0:
                        continue
                except (ValueError, TypeError):
                    continue

                # Find matching interval
                for interval_time in intervals:
                    next_interval = interval_time + timedelta(hours=1)
                    if interval_time <= parsed_time < next_interval:
                        station_data[station_id][interval_time].append(rainfall_float)
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
    ) -> List[PrecipitationDataPoint]:
        """Format interval data with smart labeling."""
        result = []

        for interval_time in intervals:
            rainfall_values = interval_data.get(interval_time, [])

            # Calculate average, or 0 if no data
            avg_rainfall = sum(rainfall_values) / len(rainfall_values) if rainfall_values else 0

            # Classify intensity using MetricsService
            intensity = self.metrics_service.get_rainfall_level(avg_rainfall)

            # Format label
            label = self._format_time_label(interval_time)
            day_label = self._get_day_label(interval_time, display_date)

            # Determine if this hour should show label on X-axis
            show_label = (interval_time.hour % LABEL_INTERVAL_HOURS == 0)

            result.append(PrecipitationDataPoint(
                label=label,
                y=round(avg_rainfall, 1),
                intensity=intensity,
                day=day_label,
                timestamp=interval_time.isoformat(),
                count=len(rainfall_values),
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

    def get_summary_statistics(self, data_points: List[PrecipitationDataPoint]) -> Dict:
        """Calculate summary statistics for precipitation data."""
        if not data_points:
            return {
                'total_rainfall': 0,
                'average_rainfall': 0,
                'max_rainfall': 0,
                'min_rainfall': 0,
                'intervals_with_rain': 0,
                'total_intervals': 0
            }

        rainfall_values = [point.y for point in data_points]
        intervals_with_rain = sum(1 for point in data_points if point.y > 0)

        return {
            'total_rainfall': round(sum(rainfall_values), 1),
            'average_rainfall': round(sum(rainfall_values) / len(rainfall_values), 1),
            'max_rainfall': max(rainfall_values),
            'min_rainfall': min(rainfall_values),
            'intervals_with_rain': intervals_with_rain,
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