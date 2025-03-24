"""
Mock implementation of the Billing integration module for testing.
"""
import json
import httpx
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime


class BillingIntegration:
    """
    Integration with the Billing API for managing invoices and payments.
    """
    
    def __init__(self, api_url: str, api_key: str, timeout: float = 10.0):
        """
        Initialize the Billing integration.
        
        Args:
            api_url: The base URL of the Billing API
            api_key: The API key for authentication
            timeout: The timeout for API requests in seconds
        """
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
    
    async def _make_request(self, method: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the Billing API.
        
        Args:
            method: The HTTP method to use
            endpoint: The API endpoint
            data: The request data
            
        Returns:
            The response data as a dictionary
            
        Raises:
            Exception: If the API request fails
        """
        url = f"{self.api_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert Decimal objects to strings for JSON serialization
        def decimal_serializer(obj):
            if isinstance(obj, Decimal):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=json.dumps(data, default=decimal_serializer),
                    timeout=self.timeout
                )
                
                response_data = response.json()
                
                if response.status_code >= 400:
                    raise Exception(f"Billing API error: {response_data.get('message', 'Unknown error')}")
                
                return response_data
        except httpx.TimeoutException as e:
            raise Exception(f"Billing API request timed out: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Billing API HTTP error: {str(e)}")
        except Exception as e:
            raise Exception(f"Billing API request failed: {str(e)}")
    
    async def create_invoice_item(self, user_id: int, amount: Decimal, description: str) -> Dict[str, Any]:
        """
        Create an invoice item for a user.
        
        Args:
            user_id: The ID of the user
            amount: The amount to charge
            description: The description of the charge
            
        Returns:
            The response data as a dictionary
        """
        data = {
            "user_id": user_id,
            "amount": amount,
            "description": description
        }
        
        return await self._make_request("POST", "invoices/items/create", data)
    
    async def calculate_prorated_amount(
        self, user_id: int, old_plan_id: int, new_plan_id: int, change_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate the prorated amount for a plan change.
        
        Args:
            user_id: The ID of the user
            old_plan_id: The ID of the old plan
            new_plan_id: The ID of the new plan
            change_date: The date of the plan change
            
        Returns:
            The response data as a dictionary with prorated_refund, prorated_charge, and net_charge
        """
        data = {
            "user_id": user_id,
            "old_plan_id": old_plan_id,
            "new_plan_id": new_plan_id,
            "change_date": change_date
        }
        
        return await self._make_request("POST", "billing/prorate", data)
    
    async def charge_overage_fee(self, user_id: int, amount: Decimal, usage_bytes: int) -> Dict[str, Any]:
        """
        Charge an overage fee for exceeding data cap.
        
        Args:
            user_id: The ID of the user
            amount: The amount to charge
            usage_bytes: The usage in bytes that caused the overage
            
        Returns:
            The response data as a dictionary
        """
        data = {
            "user_id": user_id,
            "amount": amount,
            "usage_bytes": usage_bytes,
            "description": f"Data cap overage fee - {usage_bytes / (1024**3):.2f} GB over limit"
        }
        
        return await self._make_request("POST", "billing/overage", data)
    
    async def create_subscription_invoice(self, user_id: int, plan_id: int, amount: Decimal) -> Dict[str, Any]:
        """
        Create a subscription invoice for a billing cycle.
        
        Args:
            user_id: The ID of the user
            plan_id: The ID of the plan
            amount: The amount to charge
            
        Returns:
            The response data as a dictionary
        """
        data = {
            "user_id": user_id,
            "plan_id": plan_id,
            "amount": amount,
            "description": "Monthly subscription"
        }
        
        return await self._make_request("POST", "invoices/create", data)
    
    async def get_user_billing_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get billing information for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            The response data as a dictionary
        """
        data = {
            "user_id": user_id
        }
        
        return await self._make_request("POST", "users/billing-info", data)
