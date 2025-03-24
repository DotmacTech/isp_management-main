"""
Unit tests for the monitoring module's alert system.

This module tests the alert system functionality for detecting threshold violations
and sending notifications based on monitoring data.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, ANY

from modules.monitoring.models import (
    AlertConfiguration, AlertHistory, AlertSeverity, AlertStatus,
    SystemMetric, MetricType, LogLevel
)
from modules.monitoring.services.alert_service import AlertService


@pytest.fixture
def mock_notification_service():
    """Provide a mock notification service for testing."""
    mock_service = MagicMock()
    mock_service.send_notification.return_value = {"success": True, "message_id": "test-123"}
    return mock_service


@pytest.fixture
def sample_alert_configurations(db_session):
    """Create sample alert configurations for testing."""
    # CPU usage alert
    cpu_alert = AlertConfiguration(
        id=1,
        name="High CPU Usage",
        description="Alert when CPU usage exceeds 90%",
        service_name="system",
        metric_type=MetricType.CPU_USAGE,
        condition_type="threshold",
        threshold_value=90.0,
        comparison_operator=">",
        severity=AlertSeverity.WARNING,
        is_active=True,
        cooldown_minutes=15,
        notification_channels=json.dumps(["email", "sms"])
    )
    
    # Network latency alert
    latency_alert = AlertConfiguration(
        id=2,
        name="High Network Latency",
        description="Alert when network latency exceeds 200ms",
        service_name="network",
        metric_type=MetricType.LATENCY,
        condition_type="threshold",
        threshold_value=200.0,
        comparison_operator=">",
        severity=AlertSeverity.WARNING,
        is_active=True,
        cooldown_minutes=10,
        notification_channels=json.dumps(["email"])
    )
    
    # Error rate alert
    error_alert = AlertConfiguration(
        id=3,
        name="High Error Rate",
        description="Alert when error rate exceeds 5%",
        service_name="api",
        metric_type=MetricType.ERROR_RATE,
        condition_type="threshold",
        threshold_value=5.0,
        comparison_operator=">",
        severity=AlertSeverity.CRITICAL,
        is_active=True,
        cooldown_minutes=5,
        notification_channels=json.dumps(["email", "slack"])
    )
    
    # Disk usage alert
    disk_alert = AlertConfiguration(
        id=4,
        name="High Disk Usage",
        description="Alert when disk usage exceeds 85%",
        service_name="storage",
        metric_type=MetricType.DISK_USAGE,
        condition_type="threshold",
        threshold_value=85.0,
        comparison_operator=">",
        severity=AlertSeverity.WARNING,
        is_active=True,
        cooldown_minutes=60,
        notification_channels=json.dumps(["email"])
    )
    
    # Inactive alert
    inactive_alert = AlertConfiguration(
        id=5,
        name="Inactive Alert",
        description="This alert is inactive",
        service_name="system",
        metric_type=MetricType.MEMORY_USAGE,
        condition_type="threshold",
        threshold_value=95.0,
        comparison_operator=">",
        severity=AlertSeverity.WARNING,
        is_active=False,
        cooldown_minutes=15,
        notification_channels=json.dumps(["email"])
    )
    
    # Pattern-based log alert
    log_alert = AlertConfiguration(
        id=6,
        name="Critical Error Log",
        description="Alert when critical error logs are detected",
        service_name="api",
        log_level=LogLevel.ERROR,
        condition_type="pattern",
        pattern="database connection failed",
        comparison_operator="contains",
        severity=AlertSeverity.CRITICAL,
        is_active=True,
        cooldown_minutes=5,
        notification_channels=json.dumps(["email", "slack"])
    )
    
    db_session.add_all([cpu_alert, latency_alert, error_alert, disk_alert, inactive_alert, log_alert])
    db_session.commit()
    
    return {
        "cpu": cpu_alert,
        "latency": latency_alert,
        "error": error_alert,
        "disk": disk_alert,
        "inactive": inactive_alert,
        "log": log_alert
    }


@pytest.fixture
def sample_metrics(db_session):
    """Create sample metrics for testing alerts."""
    # CPU usage metrics
    cpu_normal = SystemMetric(
        service_name="system",
        host_name="server-1",
        metric_type=MetricType.CPU_USAGE,
        value=75.0,
        unit="%",
        timestamp=datetime.utcnow() - timedelta(minutes=10)
    )
    
    cpu_high = SystemMetric(
        service_name="system",
        host_name="server-1",
        metric_type=MetricType.CPU_USAGE,
        value=95.0,
        unit="%",
        timestamp=datetime.utcnow() - timedelta(minutes=5)
    )
    
    # Network latency metrics
    latency_normal = SystemMetric(
        service_name="network",
        host_name="router-1",
        metric_type=MetricType.LATENCY,
        value=50.0,
        unit="ms",
        timestamp=datetime.utcnow() - timedelta(minutes=10)
    )
    
    latency_high = SystemMetric(
        service_name="network",
        host_name="router-1",
        metric_type=MetricType.LATENCY,
        value=250.0,
        unit="ms",
        timestamp=datetime.utcnow() - timedelta(minutes=5)
    )
    
    # Error rate metrics
    error_normal = SystemMetric(
        service_name="api",
        host_name="api-server",
        metric_type=MetricType.ERROR_RATE,
        value=1.5,
        unit="%",
        timestamp=datetime.utcnow() - timedelta(minutes=10)
    )
    
    error_high = SystemMetric(
        service_name="api",
        host_name="api-server",
        metric_type=MetricType.ERROR_RATE,
        value=7.5,
        unit="%",
        timestamp=datetime.utcnow() - timedelta(minutes=5)
    )
    
    # Disk usage metrics
    disk_normal = SystemMetric(
        service_name="storage",
        host_name="storage-server",
        metric_type=MetricType.DISK_USAGE,
        value=70.0,
        unit="%",
        timestamp=datetime.utcnow() - timedelta(minutes=10)
    )
    
    disk_high = SystemMetric(
        service_name="storage",
        host_name="storage-server",
        metric_type=MetricType.DISK_USAGE,
        value=90.0,
        unit="%",
        timestamp=datetime.utcnow() - timedelta(minutes=5)
    )
    
    db_session.add_all([
        cpu_normal, cpu_high,
        latency_normal, latency_high,
        error_normal, error_high,
        disk_normal, disk_high
    ])
    db_session.commit()
    
    return {
        "cpu_normal": cpu_normal,
        "cpu_high": cpu_high,
        "latency_normal": latency_normal,
        "latency_high": latency_high,
        "error_normal": error_normal,
        "error_high": error_high,
        "disk_normal": disk_normal,
        "disk_high": disk_high
    }


@pytest.fixture
def sample_alert_history(db_session, sample_alert_configurations):
    """Create sample alert history for testing."""
    # Active CPU alert
    cpu_alert = AlertHistory(
        configuration_id=sample_alert_configurations["cpu"].id,
        triggered_value=95.0,
        status=AlertStatus.ACTIVE,
        message="CPU usage is at 95%, exceeding the threshold of 90%",
        triggered_at=datetime.utcnow() - timedelta(minutes=30),
        notification_sent=True
    )
    
    # Resolved latency alert
    latency_alert = AlertHistory(
        configuration_id=sample_alert_configurations["latency"].id,
        triggered_value=250.0,
        status=AlertStatus.RESOLVED,
        message="Network latency is at 250ms, exceeding the threshold of 200ms",
        triggered_at=datetime.utcnow() - timedelta(hours=2),
        resolved_at=datetime.utcnow() - timedelta(hours=1),
        resolution_notes="Network congestion resolved",
        notification_sent=True
    )
    
    # Acknowledged error alert
    error_alert = AlertHistory(
        configuration_id=sample_alert_configurations["error"].id,
        triggered_value=7.5,
        status=AlertStatus.ACKNOWLEDGED,
        message="Error rate is at 7.5%, exceeding the threshold of 5%",
        triggered_at=datetime.utcnow() - timedelta(hours=1),
        acknowledged_by=1,  # User ID
        notification_sent=True
    )
    
    db_session.add_all([cpu_alert, latency_alert, error_alert])
    db_session.commit()
    
    return {
        "cpu": cpu_alert,
        "latency": latency_alert,
        "error": error_alert
    }


class TestAlertService:
    """Tests for the AlertService class."""
    
    def test_init(self, db_session, mock_notification_service):
        """Test initializing the alert service."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        assert service.db_session == db_session
        assert service.notification_service == mock_notification_service
    
    def test_get_active_configurations(self, db_session, sample_alert_configurations, mock_notification_service):
        """Test getting active alert configurations."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get active configurations
        active_configs = service.get_active_configurations()
        
        # Check that we have the correct number of active configurations
        assert len(active_configs) == 5  # 6 total, 1 inactive
        
        # Check that inactive configuration is not included
        inactive_id = sample_alert_configurations["inactive"].id
        assert all(config.id != inactive_id for config in active_configs)
    
    def test_check_metric_alert_triggered(self, db_session, sample_alert_configurations, sample_metrics, mock_notification_service):
        """Test checking if a metric alert is triggered."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Test with CPU usage alert and high CPU metric
        cpu_config = sample_alert_configurations["cpu"]
        cpu_metric = sample_metrics["cpu_high"]
        
        # Check if alert is triggered
        is_triggered, message = service.check_metric_alert(cpu_config, cpu_metric)
        
        assert is_triggered is True
        assert "exceeding the threshold" in message
        
        # Test with CPU usage alert and normal CPU metric
        cpu_metric = sample_metrics["cpu_normal"]
        
        # Check if alert is triggered
        is_triggered, message = service.check_metric_alert(cpu_config, cpu_metric)
        
        assert is_triggered is False
        assert message is None
    
    def test_create_alert(self, db_session, sample_alert_configurations, sample_metrics, mock_notification_service):
        """Test creating a new alert."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Use disk usage alert and high disk metric
        disk_config = sample_alert_configurations["disk"]
        disk_metric = sample_metrics["disk_high"]
        
        # Create alert
        alert = service.create_alert(
            disk_config,
            triggered_value=disk_metric.value,
            message=f"Disk usage is at {disk_metric.value}%, exceeding the threshold of {disk_config.threshold_value}%",
            source_metric_id=disk_metric.id
        )
        
        assert alert.configuration_id == disk_config.id
        assert alert.triggered_value == disk_metric.value
        assert alert.status == AlertStatus.ACTIVE
        assert "exceeding the threshold" in alert.message
        assert alert.source_metric_id == disk_metric.id
        assert alert.notification_sent is False
    
    def test_send_alert_notification(self, db_session, sample_alert_configurations, mock_notification_service):
        """Test sending an alert notification."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Create a new alert
        disk_config = sample_alert_configurations["disk"]
        alert = AlertHistory(
            configuration_id=disk_config.id,
            triggered_value=90.0,
            status=AlertStatus.ACTIVE,
            message="Disk usage is at 90%, exceeding the threshold of 85%",
            triggered_at=datetime.utcnow(),
            notification_sent=False
        )
        
        db_session.add(alert)
        db_session.commit()
        
        # Send notification
        result = service.send_alert_notification(alert)
        
        assert result is True
        assert alert.notification_sent is True
        
        # Check that notification service was called
        notification_channels = json.loads(disk_config.notification_channels)
        mock_notification_service.send_notification.assert_called_once()
        call_args = mock_notification_service.send_notification.call_args[0]
        assert call_args[0] == notification_channels
        assert disk_config.name in call_args[1]  # Subject
        assert alert.message in call_args[2]  # Message
    
    def test_resolve_alert(self, db_session, sample_alert_history, mock_notification_service):
        """Test resolving an alert."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get active CPU alert
        cpu_alert = sample_alert_history["cpu"]
        
        # Resolve alert
        resolution_notes = "CPU usage has returned to normal levels"
        service.resolve_alert(cpu_alert.id, resolution_notes)
        
        # Refresh alert from database
        db_session.refresh(cpu_alert)
        
        assert cpu_alert.status == AlertStatus.RESOLVED
        assert cpu_alert.resolved_at is not None
        assert cpu_alert.resolution_notes == resolution_notes
    
    def test_acknowledge_alert(self, db_session, sample_alert_history, mock_notification_service):
        """Test acknowledging an alert."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get active CPU alert
        cpu_alert = sample_alert_history["cpu"]
        
        # Acknowledge alert
        user_id = 2
        service.acknowledge_alert(cpu_alert.id, user_id)
        
        # Refresh alert from database
        db_session.refresh(cpu_alert)
        
        assert cpu_alert.status == AlertStatus.ACKNOWLEDGED
        assert cpu_alert.acknowledged_by == user_id
    
    def test_process_metric_alerts(self, db_session, sample_alert_configurations, sample_metrics, mock_notification_service):
        """Test processing metric alerts."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Process alerts for all metrics
        with patch.object(service, 'send_alert_notification', return_value=True) as mock_send:
            alerts = service.process_metric_alerts()
            
            # We should have alerts for cpu_high, latency_high, error_high, and disk_high
            assert len(alerts) == 4
            
            # Check that notifications were sent
            assert mock_send.call_count == 4
    
    def test_get_recent_alerts(self, db_session, sample_alert_history, mock_notification_service):
        """Test getting recent alerts."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get all recent alerts
        alerts = service.get_recent_alerts()
        
        assert len(alerts) == 3
        
        # Get active alerts only
        active_alerts = service.get_recent_alerts(status=AlertStatus.ACTIVE)
        
        assert len(active_alerts) == 1
        assert active_alerts[0].status == AlertStatus.ACTIVE
        
        # Get alerts for specific configuration
        cpu_config_id = sample_alert_history["cpu"].configuration_id
        cpu_alerts = service.get_recent_alerts(configuration_id=cpu_config_id)
        
        assert len(cpu_alerts) == 1
        assert cpu_alerts[0].configuration_id == cpu_config_id
    
    def test_get_alert_statistics(self, db_session, sample_alert_history, mock_notification_service):
        """Test getting alert statistics."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get statistics
        stats = service.get_alert_statistics()
        
        assert "total_alerts" in stats
        assert stats["total_alerts"] == 3
        assert "active_alerts" in stats
        assert stats["active_alerts"] == 1
        assert "resolved_alerts" in stats
        assert stats["resolved_alerts"] == 1
        assert "acknowledged_alerts" in stats
        assert stats["acknowledged_alerts"] == 1
        assert "alerts_by_severity" in stats
        assert "alerts_by_service" in stats


class TestAlertThresholdDetection:
    """Tests for alert threshold detection functionality."""
    
    def test_detect_cpu_usage_threshold(self, db_session, sample_alert_configurations, sample_metrics, mock_notification_service):
        """Test detecting CPU usage threshold violations."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get CPU alert configuration
        cpu_config = sample_alert_configurations["cpu"]
        
        # Test with high CPU metric
        cpu_high = sample_metrics["cpu_high"]
        is_triggered, _ = service.check_metric_alert(cpu_config, cpu_high)
        assert is_triggered is True
        
        # Test with normal CPU metric
        cpu_normal = sample_metrics["cpu_normal"]
        is_triggered, _ = service.check_metric_alert(cpu_config, cpu_normal)
        assert is_triggered is False
    
    def test_detect_network_latency_threshold(self, db_session, sample_alert_configurations, sample_metrics, mock_notification_service):
        """Test detecting network latency threshold violations."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get latency alert configuration
        latency_config = sample_alert_configurations["latency"]
        
        # Test with high latency metric
        latency_high = sample_metrics["latency_high"]
        is_triggered, _ = service.check_metric_alert(latency_config, latency_high)
        assert is_triggered is True
        
        # Test with normal latency metric
        latency_normal = sample_metrics["latency_normal"]
        is_triggered, _ = service.check_metric_alert(latency_config, latency_normal)
        assert is_triggered is False
    
    def test_detect_error_rate_threshold(self, db_session, sample_alert_configurations, sample_metrics, mock_notification_service):
        """Test detecting error rate threshold violations."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get error rate alert configuration
        error_config = sample_alert_configurations["error"]
        
        # Test with high error rate metric
        error_high = sample_metrics["error_high"]
        is_triggered, _ = service.check_metric_alert(error_config, error_high)
        assert is_triggered is True
        
        # Test with normal error rate metric
        error_normal = sample_metrics["error_normal"]
        is_triggered, _ = service.check_metric_alert(error_config, error_normal)
        assert is_triggered is False
    
    def test_detect_disk_usage_threshold(self, db_session, sample_alert_configurations, sample_metrics, mock_notification_service):
        """Test detecting disk usage threshold violations."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Get disk usage alert configuration
        disk_config = sample_alert_configurations["disk"]
        
        # Test with high disk usage metric
        disk_high = sample_metrics["disk_high"]
        is_triggered, _ = service.check_metric_alert(disk_config, disk_high)
        assert is_triggered is True
        
        # Test with normal disk usage metric
        disk_normal = sample_metrics["disk_normal"]
        is_triggered, _ = service.check_metric_alert(disk_config, disk_normal)
        assert is_triggered is False


class TestAlertNotifications:
    """Tests for alert notification functionality."""
    
    def test_notification_channels(self, db_session, sample_alert_configurations, mock_notification_service):
        """Test that alert notifications are sent to the correct channels."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Create a new alert for CPU usage
        cpu_config = sample_alert_configurations["cpu"]
        alert = service.create_alert(
            cpu_config,
            triggered_value=95.0,
            message="CPU usage is at 95%, exceeding the threshold of 90%"
        )
        
        # Send notification
        service.send_alert_notification(alert)
        
        # Check that notification service was called with correct channels
        notification_channels = json.loads(cpu_config.notification_channels)
        mock_notification_service.send_notification.assert_called_once()
        call_args = mock_notification_service.send_notification.call_args[0]
        assert call_args[0] == notification_channels
    
    def test_notification_cooldown(self, db_session, sample_alert_configurations, mock_notification_service):
        """Test that alert notifications respect cooldown periods."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Create an alert that was triggered recently
        cpu_config = sample_alert_configurations["cpu"]
        recent_alert = AlertHistory(
            configuration_id=cpu_config.id,
            triggered_value=95.0,
            status=AlertStatus.ACTIVE,
            message="CPU usage is at 95%, exceeding the threshold of 90%",
            triggered_at=datetime.utcnow() - timedelta(minutes=5),  # 5 minutes ago
            notification_sent=True
        )
        
        db_session.add(recent_alert)
        db_session.commit()
        
        # Check if we should send a new notification (we shouldn't, cooldown is 15 minutes)
        should_notify = service.should_send_notification(cpu_config)
        
        assert should_notify is False
        
        # Create an alert that was triggered long ago
        old_alert = AlertHistory(
            configuration_id=cpu_config.id,
            triggered_value=95.0,
            status=AlertStatus.RESOLVED,
            message="CPU usage is at 95%, exceeding the threshold of 90%",
            triggered_at=datetime.utcnow() - timedelta(minutes=30),  # 30 minutes ago
            resolved_at=datetime.utcnow() - timedelta(minutes=25),  # 25 minutes ago
            notification_sent=True
        )
        
        db_session.add(old_alert)
        db_session.commit()
        
        # Check if we should send a new notification (we should, cooldown has passed)
        should_notify = service.should_send_notification(cpu_config)
        
        assert should_notify is True
    
    def test_notification_content(self, db_session, sample_alert_configurations, mock_notification_service):
        """Test that alert notifications contain the correct content."""
        service = AlertService(db_session, notification_service=mock_notification_service)
        
        # Create a new alert for error rate
        error_config = sample_alert_configurations["error"]
        alert = service.create_alert(
            error_config,
            triggered_value=7.5,
            message="Error rate is at 7.5%, exceeding the threshold of 5%"
        )
        
        # Send notification
        service.send_alert_notification(alert)
        
        # Check notification content
        mock_notification_service.send_notification.assert_called_once()
        call_args = mock_notification_service.send_notification.call_args[0]
        
        # Subject should contain alert name
        subject = call_args[1]
        assert error_config.name in subject
        assert error_config.severity.value.upper() in subject
        
        # Message should contain alert details
        message = call_args[2]
        assert alert.message in message
        assert str(alert.triggered_value) in message
        assert error_config.service_name in message
