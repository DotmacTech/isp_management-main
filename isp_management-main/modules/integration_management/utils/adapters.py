"""
Integration adapters for the Integration Management Module.

This module implements the adapter pattern for different integration types,
providing a consistent interface for interacting with various external services.
"""

import abc
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

from ..models.integration import Integration, IntegrationType
from .security import CredentialEncryptor

logger = logging.getLogger(__name__)


class IntegrationAdapter(abc.ABC):
    """Abstract base class for integration adapters."""
    
    def __init__(self, integration: Integration, credential_encryptor: CredentialEncryptor):
        """
        Initialize the adapter with an integration configuration.
        
        Args:
            integration: Integration configuration
            credential_encryptor: Encryptor for handling credentials
        """
        self.integration = integration
        self.credential_encryptor = credential_encryptor
        self.credentials = self._get_credentials()
        self.configuration = integration.configuration
    
    def _get_credentials(self) -> Dict[str, Any]:
        """
        Get decrypted credentials for the integration.
        
        Returns:
            Dictionary containing decrypted credentials
        """
        try:
            return self.credential_encryptor.decrypt(self.integration.encrypted_credentials)
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for integration {self.integration.id}: {str(e)}")
            return {}
    
    @abc.abstractmethod
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test the connection to the external service.
        
        Returns:
            Tuple containing a boolean indicating success and an optional error message
        """
        pass
    
    @abc.abstractmethod
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the status of the external service.
        
        Returns:
            Dictionary containing service status information
        """
        pass
    
    @classmethod
    def get_adapter_for_integration(
        cls, integration: Integration, credential_encryptor: CredentialEncryptor
    ) -> 'IntegrationAdapter':
        """
        Factory method to get the appropriate adapter for an integration.
        
        Args:
            integration: Integration configuration
            credential_encryptor: Encryptor for handling credentials
            
        Returns:
            Appropriate adapter instance for the integration type
            
        Raises:
            ValueError: If no adapter is available for the integration type
        """
        adapter_map = {
            IntegrationType.PAYMENT_GATEWAY: PaymentGatewayAdapter,
            IntegrationType.SMS_PROVIDER: SMSProviderAdapter,
            IntegrationType.EMAIL_PROVIDER: EmailProviderAdapter,
            IntegrationType.ANALYTICS: AnalyticsAdapter,
            IntegrationType.CRM: CRMAdapter,
            IntegrationType.MONITORING: MonitoringAdapter,
            IntegrationType.AUTHENTICATION: AuthenticationAdapter,
            IntegrationType.STORAGE: StorageAdapter,
            IntegrationType.CUSTOM: CustomAdapter,
        }
        
        adapter_class = adapter_map.get(integration.type)
        if not adapter_class:
            raise ValueError(f"No adapter available for integration type: {integration.type}")
        
        return adapter_class(integration, credential_encryptor)


class PaymentGatewayAdapter(IntegrationAdapter):
    """Adapter for payment gateway integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the payment gateway."""
        try:
            # Get the base URL from configuration
            base_url = self.configuration.get("base_url")
            if not base_url:
                return False, "Base URL not configured"
            
            # Get API key from credentials
            api_key = self.credentials.get("api_key")
            if not api_key:
                return False, "API key not found in credentials"
            
            # Make a test request to the payment gateway
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Use a simple endpoint for testing, like retrieving account info
            response = requests.get(
                f"{base_url}/v1/account",
                headers=headers,
                timeout=10
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Failed to connect: {response.status_code} - {response.text}"
        
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the payment gateway service."""
        status = {
            "service_type": "payment_gateway",
            "provider": self.configuration.get("provider", "unknown"),
            "is_connected": False,
            "last_checked": datetime.utcnow().isoformat(),
            "details": {}
        }
        
        try:
            # Test the connection
            is_connected, error_message = self.test_connection()
            status["is_connected"] = is_connected
            
            if not is_connected:
                status["details"]["error"] = error_message
                return status
            
            # Get additional service information if available
            base_url = self.configuration.get("base_url")
            api_key = self.credentials.get("api_key")
            
            if base_url and api_key:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Get account information
                account_response = requests.get(
                    f"{base_url}/v1/account",
                    headers=headers,
                    timeout=10
                )
                
                if account_response.status_code == 200:
                    account_data = account_response.json()
                    status["details"]["account"] = {
                        "name": account_data.get("business_name"),
                        "email": account_data.get("email"),
                        "country": account_data.get("country")
                    }
            
            return status
        
        except Exception as e:
            status["is_connected"] = False
            status["details"]["error"] = f"Error getting service status: {str(e)}"
            return status
    
    def create_payment(self, amount: float, currency: str, description: str) -> Dict[str, Any]:
        """
        Create a payment using the payment gateway.
        
        Args:
            amount: Payment amount
            currency: Currency code (e.g., USD, EUR)
            description: Payment description
            
        Returns:
            Dictionary containing payment information
        """
        try:
            # Get the base URL from configuration
            base_url = self.configuration.get("base_url")
            if not base_url:
                raise ValueError("Base URL not configured")
            
            # Get API key from credentials
            api_key = self.credentials.get("api_key")
            if not api_key:
                raise ValueError("API key not found in credentials")
            
            # Prepare the payment request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "amount": int(amount * 100),  # Convert to cents/smallest currency unit
                "currency": currency,
                "description": description
            }
            
            # Make the payment request
            response = requests.post(
                f"{base_url}/v1/payments",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Check if the request was successful
            if response.status_code in (200, 201):
                return response.json()
            else:
                raise ValueError(f"Payment failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            raise


class SMSProviderAdapter(IntegrationAdapter):
    """Adapter for SMS provider integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the SMS provider."""
        try:
            # Get the base URL from configuration
            base_url = self.configuration.get("base_url")
            if not base_url:
                return False, "Base URL not configured"
            
            # Get API credentials from credentials
            account_sid = self.credentials.get("account_sid")
            auth_token = self.credentials.get("auth_token")
            
            if not account_sid or not auth_token:
                return False, "Account SID or Auth Token not found in credentials"
            
            # Make a test request to the SMS provider
            headers = {
                "Content-Type": "application/json"
            }
            
            # Use basic auth for the request
            auth = (account_sid, auth_token)
            
            # Use a simple endpoint for testing, like retrieving account info
            response = requests.get(
                f"{base_url}/accounts/{account_sid}",
                headers=headers,
                auth=auth,
                timeout=10
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Failed to connect: {response.status_code} - {response.text}"
        
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the SMS provider service."""
        status = {
            "service_type": "sms_provider",
            "provider": self.configuration.get("provider", "unknown"),
            "is_connected": False,
            "last_checked": datetime.utcnow().isoformat(),
            "details": {}
        }
        
        try:
            # Test the connection
            is_connected, error_message = self.test_connection()
            status["is_connected"] = is_connected
            
            if not is_connected:
                status["details"]["error"] = error_message
                return status
            
            # Get additional service information if available
            base_url = self.configuration.get("base_url")
            account_sid = self.credentials.get("account_sid")
            auth_token = self.credentials.get("auth_token")
            
            if base_url and account_sid and auth_token:
                headers = {
                    "Content-Type": "application/json"
                }
                
                auth = (account_sid, auth_token)
                
                # Get account information
                account_response = requests.get(
                    f"{base_url}/accounts/{account_sid}",
                    headers=headers,
                    auth=auth,
                    timeout=10
                )
                
                if account_response.status_code == 200:
                    account_data = account_response.json()
                    status["details"]["account"] = {
                        "friendly_name": account_data.get("friendly_name"),
                        "status": account_data.get("status"),
                        "type": account_data.get("type")
                    }
            
            return status
        
        except Exception as e:
            status["is_connected"] = False
            status["details"]["error"] = f"Error getting service status: {str(e)}"
            return status
    
    def send_sms(self, to: str, body: str, from_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an SMS message.
        
        Args:
            to: Recipient phone number
            body: Message body
            from_number: Sender phone number (optional)
            
        Returns:
            Dictionary containing message information
        """
        try:
            # Get the base URL from configuration
            base_url = self.configuration.get("base_url")
            if not base_url:
                raise ValueError("Base URL not configured")
            
            # Get API credentials from credentials
            account_sid = self.credentials.get("account_sid")
            auth_token = self.credentials.get("auth_token")
            
            if not account_sid or not auth_token:
                raise ValueError("Account SID or Auth Token not found in credentials")
            
            # Get the default from number if not provided
            if not from_number:
                from_number = self.configuration.get("default_from_number")
                if not from_number:
                    raise ValueError("From number not provided and no default configured")
            
            # Prepare the SMS request
            headers = {
                "Content-Type": "application/json"
            }
            
            auth = (account_sid, auth_token)
            
            payload = {
                "To": to,
                "From": from_number,
                "Body": body
            }
            
            # Make the SMS request
            response = requests.post(
                f"{base_url}/accounts/{account_sid}/messages",
                headers=headers,
                auth=auth,
                data=payload,
                timeout=30
            )
            
            # Check if the request was successful
            if response.status_code in (200, 201):
                return response.json()
            else:
                raise ValueError(f"SMS sending failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            raise


class EmailProviderAdapter(IntegrationAdapter):
    """Adapter for email provider integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the email provider."""
        try:
            # Get the base URL from configuration
            base_url = self.configuration.get("base_url")
            if not base_url:
                return False, "Base URL not configured"
            
            # Get API key from credentials
            api_key = self.credentials.get("api_key")
            if not api_key:
                return False, "API key not found in credentials"
            
            # Make a test request to the email provider
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Use a simple endpoint for testing, like retrieving account info
            response = requests.get(
                f"{base_url}/v3/user/account",
                headers=headers,
                timeout=10
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Failed to connect: {response.status_code} - {response.text}"
        
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the email provider service."""
        status = {
            "service_type": "email_provider",
            "provider": self.configuration.get("provider", "unknown"),
            "is_connected": False,
            "last_checked": datetime.utcnow().isoformat(),
            "details": {}
        }
        
        try:
            # Test the connection
            is_connected, error_message = self.test_connection()
            status["is_connected"] = is_connected
            
            if not is_connected:
                status["details"]["error"] = error_message
                return status
            
            # Get additional service information if available
            base_url = self.configuration.get("base_url")
            api_key = self.credentials.get("api_key")
            
            if base_url and api_key:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Get account information
                account_response = requests.get(
                    f"{base_url}/v3/user/account",
                    headers=headers,
                    timeout=10
                )
                
                if account_response.status_code == 200:
                    account_data = account_response.json()
                    status["details"]["account"] = {
                        "name": account_data.get("first_name", "") + " " + account_data.get("last_name", ""),
                        "email": account_data.get("email"),
                        "type": account_data.get("type")
                    }
            
            return status
        
        except Exception as e:
            status["is_connected"] = False
            status["details"]["error"] = f"Error getting service status: {str(e)}"
            return status


class AnalyticsAdapter(IntegrationAdapter):
    """Adapter for analytics integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the analytics service."""
        # Implementation for analytics service connection test
        return True, None
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the analytics service."""
        # Implementation for analytics service status
        return {"service_type": "analytics", "is_connected": True}


class CRMAdapter(IntegrationAdapter):
    """Adapter for CRM integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the CRM service."""
        # Implementation for CRM service connection test
        return True, None
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the CRM service."""
        # Implementation for CRM service status
        return {"service_type": "crm", "is_connected": True}


class MonitoringAdapter(IntegrationAdapter):
    """Adapter for monitoring integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the monitoring service."""
        # Implementation for monitoring service connection test
        return True, None
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the monitoring service."""
        # Implementation for monitoring service status
        return {"service_type": "monitoring", "is_connected": True}


class AuthenticationAdapter(IntegrationAdapter):
    """Adapter for authentication integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the authentication service."""
        # Implementation for authentication service connection test
        return True, None
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the authentication service."""
        # Implementation for authentication service status
        return {"service_type": "authentication", "is_connected": True}


class StorageAdapter(IntegrationAdapter):
    """Adapter for storage integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the storage service."""
        # Implementation for storage service connection test
        return True, None
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the storage service."""
        # Implementation for storage service status
        return {"service_type": "storage", "is_connected": True}


class CustomAdapter(IntegrationAdapter):
    """Adapter for custom integrations."""
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the custom service."""
        # For custom integrations, we'll use a configurable endpoint for testing
        try:
            # Get the health check URL from configuration
            health_check_url = self.configuration.get("health_check_url")
            if not health_check_url:
                return False, "Health check URL not configured"
            
            # Get headers from configuration
            headers = self.configuration.get("headers", {})
            
            # Add authentication if configured
            auth_type = self.configuration.get("auth_type")
            if auth_type == "bearer":
                token = self.credentials.get("token")
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            elif auth_type == "basic":
                username = self.credentials.get("username")
                password = self.credentials.get("password")
                if username and password:
                    auth = (username, password)
                else:
                    auth = None
            else:
                auth = None
            
            # Make the health check request
            response = requests.get(
                health_check_url,
                headers=headers,
                auth=auth if auth_type == "basic" else None,
                timeout=30
            )
            
            # Check if the request was successful
            if response.status_code in (200, 201, 202, 204):
                return True, None
            else:
                return False, f"Failed to connect: {response.status_code} - {response.text}"
        
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the custom service."""
        status = {
            "service_type": "custom",
            "name": self.integration.name,
            "is_connected": False,
            "last_checked": datetime.utcnow().isoformat(),
            "details": {}
        }
        
        try:
            # Test the connection
            is_connected, error_message = self.test_connection()
            status["is_connected"] = is_connected
            
            if not is_connected:
                status["details"]["error"] = error_message
            
            return status
        
        except Exception as e:
            status["is_connected"] = False
            status["details"]["error"] = f"Error getting service status: {str(e)}"
            return status
