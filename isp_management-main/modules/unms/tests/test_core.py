"""
Unit tests for the UNMS module core functionality.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from modules.unms.core import UNMSAPI
from modules.unms.exceptions import AuthenticationError, UNMSAPIError


class TestUNMSCore(unittest.TestCase):
    """
    Tests for the UNMS core functionality.
    """
    
    def setUp(self):
        """
        Set up test fixtures.
        """
        self.base_url = "https://unms.example.com"
        self.username = "test_user"
        self.password = "test_password"
        
        # Create API client with mocked requests
        with patch('modules.unms.core.requests.Session'):
            self.api = UNMSAPI(
                base_url=self.base_url,
                username=self.username,
                password=self.password
            )
    
    def test_initialization(self):
        """
        Test API client initialization.
        """
        self.assertEqual(self.api.base_url, self.base_url)
        self.assertEqual(self.api._username, self.username)
        self.assertEqual(self.api._password, self.password)
    
    @patch('modules.unms.core.requests.Session.request')
    def test_request(self, mock_request):
        """
        Test API request method.
        """
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test_data"}
        mock_request.return_value = mock_response
        
        # Make request
        result = self.api.request("GET", "test/endpoint")
        
        # Verify request was made properly
        mock_request.assert_called_once()
        self.assertEqual(result, {"data": "test_data"})
    
    @patch('modules.unms.core.requests.Session.request')
    def test_auth_error(self, mock_request):
        """
        Test authentication error handling.
        """
        # Mock failed auth response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}
        mock_request.return_value = mock_response
        
        # Verify AuthenticationError is raised
        with self.assertRaises(AuthenticationError):
            self.api.request("GET", "test/endpoint")
    
    @patch('modules.unms.core.requests.Session.request')
    def test_api_error(self, mock_request):
        """
        Test API error handling.
        """
        # Mock failed API response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Server error"}
        mock_request.return_value = mock_response
        
        # Verify UNMSAPIError is raised
        with self.assertRaises(UNMSAPIError):
            self.api.request("GET", "test/endpoint")


if __name__ == '__main__':
    unittest.main()
