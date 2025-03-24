"""
Unit tests for the metrics collection module.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import unittest
from unittest.mock import patch, MagicMock
import time
import os

from core.metrics import MetricsCollector, timed


class TestMetricsCollector(unittest.TestCase):
    """Test cases for the MetricsCollector class."""

    def setUp(self):
        """Set up test environment."""
        # Save original environment variables
        self.original_env = os.environ.copy()
        
        # Set environment variables for testing
        os.environ["METRICS_BACKEND"] = "logging"
        
        # Create a metrics collector
        self.metrics = MetricsCollector("test_namespace")
    
    def tearDown(self):
        """Tear down test environment."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_initialization(self):
        """Test initialization of the metrics collector."""
        self.assertEqual(self.metrics.namespace, "test_namespace")
        self.assertEqual(self.metrics.backend, "logging")
    
    def test_increment(self):
        """Test increment method."""
        with patch("logging.Logger.info") as mock_info:
            self.metrics.increment("test_metric")
            mock_info.assert_called_once()
            self.assertIn("test_namespace.test_metric", mock_info.call_args[0][0])
            self.assertIn("+1", mock_info.call_args[0][0])
    
    def test_increment_with_value(self):
        """Test increment method with a specific value."""
        with patch("logging.Logger.info") as mock_info:
            self.metrics.increment("test_metric", 5)
            mock_info.assert_called_once()
            self.assertIn("test_namespace.test_metric", mock_info.call_args[0][0])
            self.assertIn("+5", mock_info.call_args[0][0])
    
    def test_increment_with_tags(self):
        """Test increment method with tags."""
        with patch("logging.Logger.info") as mock_info:
            self.metrics.increment("test_metric", tags={"tag1": "value1", "tag2": "value2"})
            mock_info.assert_called_once()
            self.assertIn("test_namespace.test_metric", mock_info.call_args[0][0])
            self.assertIn("tag1=value1", mock_info.call_args[0][0])
            self.assertIn("tag2=value2", mock_info.call_args[0][0])
    
    def test_gauge(self):
        """Test gauge method."""
        with patch("logging.Logger.info") as mock_info:
            self.metrics.gauge("test_metric", 42.5)
            mock_info.assert_called_once()
            self.assertIn("test_namespace.test_metric", mock_info.call_args[0][0])
            self.assertIn("= 42.5", mock_info.call_args[0][0])
    
    def test_gauge_with_tags(self):
        """Test gauge method with tags."""
        with patch("logging.Logger.info") as mock_info:
            self.metrics.gauge("test_metric", 42.5, tags={"tag1": "value1", "tag2": "value2"})
            mock_info.assert_called_once()
            self.assertIn("test_namespace.test_metric", mock_info.call_args[0][0])
            self.assertIn("= 42.5", mock_info.call_args[0][0])
            self.assertIn("tag1=value1", mock_info.call_args[0][0])
            self.assertIn("tag2=value2", mock_info.call_args[0][0])
    
    def test_record(self):
        """Test record method."""
        with patch("logging.Logger.info") as mock_info:
            self.metrics.record("test_metric", 0.123)
            mock_info.assert_called_once()
            self.assertIn("test_namespace.test_metric", mock_info.call_args[0][0])
            self.assertIn("= 0.123", mock_info.call_args[0][0])
    
    def test_record_with_tags(self):
        """Test record method with tags."""
        with patch("logging.Logger.info") as mock_info:
            self.metrics.record("test_metric", 0.123, tags={"tag1": "value1", "tag2": "value2"})
            mock_info.assert_called_once()
            self.assertIn("test_namespace.test_metric", mock_info.call_args[0][0])
            self.assertIn("= 0.123", mock_info.call_args[0][0])
            self.assertIn("tag1=value1", mock_info.call_args[0][0])
            self.assertIn("tag2=value2", mock_info.call_args[0][0])
    
    @patch("core.metrics.MetricsCollector")
    def test_timed_decorator(self, mock_metrics_collector):
        """Test timed decorator."""
        # Create a mock metrics collector
        mock_collector = MagicMock()
        mock_metrics_collector.return_value = mock_collector
        
        # Define a function to time
        @timed("test_timing")
        def test_function():
            time.sleep(0.01)
            return "test_result"
        
        # Call the function
        result = test_function()
        
        # Check that the function returned the correct result
        self.assertEqual(result, "test_result")
        
        # Check that the metrics collector was created with the correct namespace
        mock_metrics_collector.assert_called_once_with("test_metrics")
        
        # Check that the record method was called with the correct metric name
        mock_collector.record.assert_called_once()
        self.assertEqual(mock_collector.record.call_args[0][0], "test_timing")
        
        # Check that the execution time is a positive number
        self.assertGreater(mock_collector.record.call_args[0][1], 0)
        
        # Check that the tags include status=success
        self.assertEqual(mock_collector.record.call_args[0][2]["status"], "success")
    
    @patch("core.metrics.MetricsCollector")
    def test_timed_decorator_with_exception(self, mock_metrics_collector):
        """Test timed decorator when the function raises an exception."""
        # Create a mock metrics collector
        mock_collector = MagicMock()
        mock_metrics_collector.return_value = mock_collector
        
        # Define a function that raises an exception
        @timed("test_timing")
        def test_function():
            time.sleep(0.01)
            raise ValueError("test_error")
        
        # Call the function and catch the exception
        with self.assertRaises(ValueError):
            test_function()
        
        # Check that the metrics collector was created with the correct namespace
        mock_metrics_collector.assert_called_once_with("test_metrics")
        
        # Check that the record method was called with the correct metric name
        mock_collector.record.assert_called_once()
        self.assertEqual(mock_collector.record.call_args[0][0], "test_timing")
        
        # Check that the execution time is a positive number
        self.assertGreater(mock_collector.record.call_args[0][1], 0)
        
        # Check that the tags include status=error and the error message
        self.assertEqual(mock_collector.record.call_args[0][2]["status"], "error")
        self.assertEqual(mock_collector.record.call_args[0][2]["error"], "test_error")


class TestElasticsearchMetricsCollector(unittest.TestCase):
    """Test cases for the MetricsCollector class with Elasticsearch backend."""
    
    @patch("elasticsearch.Elasticsearch")
    def setUp(self, mock_elasticsearch):
        """Set up test environment."""
        # Save original environment variables
        self.original_env = os.environ.copy()
        
        # Create a mock Elasticsearch client
        self.mock_es_client = MagicMock()
        mock_elasticsearch.return_value = self.mock_es_client
        
        # Create a metrics collector with patched _initialize_backend method
        with patch.object(MetricsCollector, '_initialize_backend'):
            self.metrics = MetricsCollector("test_namespace")
            
        # Manually set the backend to elasticsearch
        self.metrics.backend = "elasticsearch"
        self.metrics.client = self.mock_es_client
        self.metrics.index = f"metrics-{self.metrics.namespace}"
    
    def tearDown(self):
        """Tear down test environment."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_initialization(self):
        """Test initialization of the metrics collector with Elasticsearch backend."""
        self.assertEqual(self.metrics.namespace, "test_namespace")
        self.assertEqual(self.metrics.backend, "elasticsearch")
        self.assertEqual(self.metrics.index, "metrics-test_namespace")
    
    def test_increment(self):
        """Test increment method with Elasticsearch backend."""
        self.metrics.increment("test_metric")
        
        # Check that the index method was called with the correct parameters
        self.mock_es_client.index.assert_called_once()
        self.assertEqual(self.mock_es_client.index.call_args[1]["index"], "metrics-test_namespace")
        
        # Check the document structure
        doc = self.mock_es_client.index.call_args[1]["document"]
        self.assertEqual(doc["type"], "counter")
        self.assertEqual(doc["metric"], "test_metric")
        self.assertEqual(doc["value"], 1)
        self.assertEqual(doc["tags"], {})
    
    def test_increment_with_value_and_tags(self):
        """Test increment method with a specific value and tags with Elasticsearch backend."""
        self.metrics.increment("test_metric", 5, tags={"tag1": "value1", "tag2": "value2"})
        
        # Check that the index method was called with the correct parameters
        self.mock_es_client.index.assert_called_once()
        self.assertEqual(self.mock_es_client.index.call_args[1]["index"], "metrics-test_namespace")
        
        # Check the document structure
        doc = self.mock_es_client.index.call_args[1]["document"]
        self.assertEqual(doc["type"], "counter")
        self.assertEqual(doc["metric"], "test_metric")
        self.assertEqual(doc["value"], 5)
        self.assertEqual(doc["tags"], {"tag1": "value1", "tag2": "value2"})
    
    def test_gauge(self):
        """Test gauge method with Elasticsearch backend."""
        self.metrics.gauge("test_metric", 42.5)
        
        # Check that the index method was called with the correct parameters
        self.mock_es_client.index.assert_called_once()
        self.assertEqual(self.mock_es_client.index.call_args[1]["index"], "metrics-test_namespace")
        
        # Check the document structure
        doc = self.mock_es_client.index.call_args[1]["document"]
        self.assertEqual(doc["type"], "gauge")
        self.assertEqual(doc["metric"], "test_metric")
        self.assertEqual(doc["value"], 42.5)
        self.assertEqual(doc["tags"], {})
    
    def test_record(self):
        """Test record method with Elasticsearch backend."""
        self.metrics.record("test_metric", 0.123)
        
        # Check that the index method was called with the correct parameters
        self.mock_es_client.index.assert_called_once()
        self.assertEqual(self.mock_es_client.index.call_args[1]["index"], "metrics-test_namespace")
        
        # Check the document structure
        doc = self.mock_es_client.index.call_args[1]["document"]
        self.assertEqual(doc["type"], "histogram")
        self.assertEqual(doc["metric"], "test_metric")
        self.assertEqual(doc["value"], 0.123)
        self.assertEqual(doc["tags"], {})
    
    @patch("logging.Logger.error")
    def test_elasticsearch_error_handling(self, mock_error):
        """Test error handling when Elasticsearch indexing fails."""
        # Make the index method raise an exception
        self.mock_es_client.index.side_effect = Exception("Test error")
        
        # This should not raise an exception
        self.metrics.increment("test_metric")
            
        # Check that the error was logged
        mock_error.assert_called_once()
        self.assertIn("Error indexing metric to Elasticsearch", mock_error.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
