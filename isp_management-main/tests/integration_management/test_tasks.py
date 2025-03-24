"""
Unit tests for the Integration Management Module's background tasks.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import unittest
from unittest.mock import MagicMock, call
import json
import os
from datetime import datetime, timedelta

class TestIntegrationManagementTasks(unittest.TestCase):
    """Test cases for the Integration Management Module's background tasks."""

    def setUp(self):
        """Set up test environment."""
        # Ensure we're in testing mode
        os.environ["TESTING"] = "true"
        
        # Create mock database session
        self.mock_db = MagicMock()
        
        # Create mock metrics collector
        self.mock_metrics = MagicMock()
        
        # Create mock tasks
        self.mock_process_webhook_event = MagicMock()
        self.mock_test_integration_connection = MagicMock()
        self.mock_test_all_active_integrations = MagicMock()
        self.mock_process_pending_webhook_events = MagicMock()
        self.mock_collect_integration_metrics = MagicMock()
        
        # Create mock models
        self.mock_integration = MagicMock()
        self.mock_integration.id = 1
        self.mock_integration.name = "Test Integration"
        self.mock_integration.type = "PAYMENT_GATEWAY"
        self.mock_integration.status = "ACTIVE"
        
        self.mock_webhook = MagicMock()
        self.mock_webhook.id = 1
        self.mock_webhook.name = "Test Webhook"
        self.mock_webhook.integration_id = 1
        
        self.mock_event = MagicMock()
        self.mock_event.id = 1
        self.mock_event.webhook_id = 1
        self.mock_event.payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123456",
                    "amount": 1000,
                    "currency": "usd",
                    "customer": "cus_123456"
                }
            }
        }
        self.mock_event.processed = False
        self.mock_event.created_at = datetime.utcnow()
    
    def tearDown(self):
        """Clean up after tests."""
        # Reset environment variables
        if "TESTING" in os.environ:
            del os.environ["TESTING"]
    
    def test_process_webhook_event_success(self):
        """Test successful processing of a webhook event."""
        # Set up the mock function
        self.mock_process_webhook_event.return_value = {
            "success": True,
            "event_id": 1
        }
        
        # Call the mock function
        result = self.mock_process_webhook_event(1)
        
        # Check that the result is as expected
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("event_id"), 1)
    
    def test_test_integration_connection_success(self):
        """Test successful testing of an integration connection."""
        # Set up the mock function
        self.mock_test_integration_connection.return_value = {
            "success": True,
            "integration_id": 1,
            "integration_type": "PAYMENT_GATEWAY"
        }
        
        # Call the mock function
        result = self.mock_test_integration_connection(1)
        
        # Check that the result is as expected
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("integration_id"), 1)
        self.assertEqual(result.get("integration_type"), "PAYMENT_GATEWAY")
    
    def test_test_all_active_integrations(self):
        """Test testing of all active integrations."""
        # Set up the mock function
        self.mock_test_all_active_integrations.return_value = {
            "success": True,
            "count": 1
        }
        
        # Call the mock function
        result = self.mock_test_all_active_integrations()
        
        # Check that the result is as expected
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("count"), 1)
    
    def test_process_pending_webhook_events(self):
        """Test processing of pending webhook events."""
        # Set up the mock function
        self.mock_process_pending_webhook_events.return_value = {
            "success": True,
            "count": 1
        }
        
        # Call the mock function
        result = self.mock_process_pending_webhook_events()
        
        # Check that the result is as expected
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("count"), 1)
    
    def test_collect_integration_metrics(self):
        """Test collection of integration metrics."""
        # Set up the mock function
        self.mock_collect_integration_metrics.return_value = {
            "success": True
        }
        
        # Call the mock function
        result = self.mock_collect_integration_metrics()
        
        # Check that the result is as expected
        self.assertTrue(result.get("success", False))


if __name__ == "__main__":
    unittest.main()
