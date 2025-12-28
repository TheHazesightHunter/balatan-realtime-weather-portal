# tests/test_metrics_service.py
"""
Unit tests for MetricsService

Run with: python tests/test_metrics_service.py
"""

import sys
import os

# Add parent directory to path so we can import services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.metrics_service import MetricsService, AlertThresholds, DashboardMetrics


def test_critical_water_level():
    """Test that 11m+ water triggers critical alert"""
    service = MetricsService()
    
    test_data = {
        'St1': {'WaterLevel': 11.5, 'HourlyRain': 0, 'WindSpeed': 0}
    }
    
    metrics = service.calculate_dashboard_metrics(test_data)
    
    assert metrics.critical_count == 1, f"Expected 1 critical, got {metrics.critical_count}"
    assert metrics.warning_count == 0, f"Expected 0 warnings, got {metrics.warning_count}"
    print("[PASS] Critical water level (11m+) works!")


def test_warning_water_level():
    """Test that 9m+ water triggers warning alert"""
    service = MetricsService()
    
    test_data = {
        'St1': {'WaterLevel': 9.5, 'HourlyRain': 0, 'WindSpeed': 0}
    }
    
    metrics = service.calculate_dashboard_metrics(test_data)
    
    assert metrics.critical_count == 0
    assert metrics.warning_count == 1, f"Expected 1 warning, got {metrics.warning_count}"
    assert metrics.alert_count == 0
    print("[PASS] Warning water level (9m+) works!")


def test_alert_water_level():
    """Test that 8m+ water triggers alert"""
    service = MetricsService()
    
    test_data = {
        'St1': {'WaterLevel': 8.5, 'HourlyRain': 0, 'WindSpeed': 0}
    }
    
    metrics = service.calculate_dashboard_metrics(test_data)
    
    assert metrics.critical_count == 0
    assert metrics.warning_count == 0
    assert metrics.alert_count == 1, f"Expected 1 alert, got {metrics.alert_count}"
    print("[PASS] Alert water level (8m+) works!")


def test_advisory_water_level():
    """Test that 7m+ water triggers advisory"""
    service = MetricsService()
    
    test_data = {
        'St1': {'WaterLevel': 7.5, 'HourlyRain': 0, 'WindSpeed': 0}
    }
    
    metrics = service.calculate_dashboard_metrics(test_data)
    
    assert metrics.critical_count == 0
    assert metrics.warning_count == 0
    assert metrics.alert_count == 0
    assert metrics.advisory_count == 1, f"Expected 1 advisory, got {metrics.advisory_count}"
    print("[PASS] Advisory water level (7m+) works!")


def test_normal_water_level():
    """Test that <7m water is normal (no alerts)"""
    service = MetricsService()
    
    test_data = {
        'St1': {'WaterLevel': 6.0, 'HourlyRain': 0, 'WindSpeed': 0}
    }
    
    metrics = service.calculate_dashboard_metrics(test_data)
    
    assert metrics.critical_count == 0
    assert metrics.warning_count == 0
    assert metrics.alert_count == 0
    assert metrics.advisory_count == 0
    print("[PASS] Normal water level (<7m) works!")


def test_multiple_stations():
    """Test multiple stations with different alert levels"""
    service = MetricsService()
    
    test_data = {
        'St1': {'WaterLevel': 11.5, 'HourlyRain': 0, 'WindSpeed': 0},  # Critical
        'St2': {'WaterLevel': 9.5, 'HourlyRain': 0, 'WindSpeed': 0},   # Warning
        'St3': {'WaterLevel': 8.5, 'HourlyRain': 0, 'WindSpeed': 0},   # Alert
        'St4': {'WaterLevel': 7.5, 'HourlyRain': 0, 'WindSpeed': 0},   # Advisory
        'St5': {'WaterLevel': 6.0, 'HourlyRain': 0, 'WindSpeed': 0},   # Normal
    }
    
    metrics = service.calculate_dashboard_metrics(test_data)
    
    assert metrics.critical_count == 1
    assert metrics.warning_count == 1
    assert metrics.alert_count == 1
    assert metrics.advisory_count == 1
    assert metrics.online_sensors == 5
    print("[PASS] Multiple stations work correctly!")


def test_boundary_values():
    """Test exact threshold boundary values"""
    service = MetricsService()
    
    # Test exactly 11.0m (should be critical)
    test_data = {'St1': {'WaterLevel': 11.0, 'HourlyRain': 0, 'WindSpeed': 0}}
    metrics = service.calculate_dashboard_metrics(test_data)
    assert metrics.critical_count == 1, "11.0m should trigger critical"
    
    # Test exactly 9.0m (should be warning)
    test_data = {'St1': {'WaterLevel': 9.0, 'HourlyRain': 0, 'WindSpeed': 0}}
    metrics = service.calculate_dashboard_metrics(test_data)
    assert metrics.warning_count == 1, "9.0m should trigger warning"
    
    # Test exactly 8.0m (should be alert)
    test_data = {'St1': {'WaterLevel': 8.0, 'HourlyRain': 0, 'WindSpeed': 0}}
    metrics = service.calculate_dashboard_metrics(test_data)
    assert metrics.alert_count == 1, "8.0m should trigger alert"
    
    # Test exactly 7.0m (should be advisory)
    test_data = {'St1': {'WaterLevel': 7.0, 'HourlyRain': 0, 'WindSpeed': 0}}
    metrics = service.calculate_dashboard_metrics(test_data)
    assert metrics.advisory_count == 1, "7.0m should trigger advisory"
    
    print("[PASS] Boundary values work correctly!")


def test_rainfall_triggers():
    """Test that high rainfall also triggers alerts"""
    service = MetricsService()
    
    # Critical rainfall (50mm/h)
    test_data = {'St1': {'WaterLevel': 0, 'HourlyRain': 55, 'WindSpeed': 0}}
    metrics = service.calculate_dashboard_metrics(test_data)
    assert metrics.critical_count == 1, "50mm+ rain should trigger critical"
    
    print("[PASS] Rainfall thresholds work!")


def test_wind_triggers():
    """Test that high wind also triggers alerts"""
    service = MetricsService()
    
    # Critical wind (25 m/s = 90 km/h)
    test_data = {'St1': {'WaterLevel': 0, 'HourlyRain': 0, 'WindSpeed': 26}}
    metrics = service.calculate_dashboard_metrics(test_data)
    assert metrics.critical_count == 1, "25m/s+ wind should trigger critical"
    
    print("[PASS] Wind thresholds work!")


def test_empty_data():
    """Test that empty data doesn't crash"""
    service = MetricsService()
    
    metrics = service.calculate_dashboard_metrics({})
    
    assert metrics.critical_count == 0
    assert metrics.warning_count == 0
    assert metrics.online_sensors == 0
    print("[PASS] Empty data handled gracefully!")


def run_all_tests():
    """Run all tests and show summary"""
    print("\n" + "="*60)
    print("RUNNING METRICS SERVICE TESTS")
    print("="*60 + "\n")
    
    tests = [
        ("Critical Water Level", test_critical_water_level),
        ("Warning Water Level", test_warning_water_level),
        ("Alert Water Level", test_alert_water_level),
        ("Advisory Water Level", test_advisory_water_level),
        ("Normal Water Level", test_normal_water_level),
        ("Multiple Stations", test_multiple_stations),
        ("Boundary Values", test_boundary_values),
        ("Rainfall Triggers", test_rainfall_triggers),
        ("Wind Triggers", test_wind_triggers),
        ("Empty Data", test_empty_data),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_name} - {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_name} - {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    if failed == 0:
        print("SUCCESS! All tests passed! Your thresholds are working perfectly!")
    else:
        print("WARNING: Some tests failed. Check the errors above.")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
    