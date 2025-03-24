"""
Billing Integration for the Tariff Enforcement Module.

This module handles the integration between the Tariff Enforcement Module and the Billing
Module, ensuring proper synchronization of tariff plans, billing cycles, and charges.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
import httpx
from fastapi import HTTPException

from backend_core.config import settings
from backend_core.logging import get_logger
from modules.tariff.monitoring import tariff_monitoring

# Configure logger
logger = get_logger(__name__)


class BillingIntegration:
    """
    Class for integrating with the Billing Module.
    
    This class provides methods for creating invoices, calculating prorated charges,
    handling overage fees, and synchronizing billing cycles with tariff plans.
    """
    
    def __init__(self):
        """Initialize the BillingIntegration instance."""
        self.billing_api_url = settings.BILLING_API_URL
        self.api_key = settings.BILLING_API_KEY
        self.timeout = settings.BILLING_API_TIMEOUT or 10.0
        
        # Default headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Source": "tariff-module"
        }
    
    async def create_invoice_item(self, user_id: int, amount: Decimal, 
                                 description: str, item_type: str = "tariff_plan",
                                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an invoice item in the billing system.
        
        Args:
            user_id: The ID of the user
            amount: The amount to charge
            description: Description of the charge
            item_type: Type of the invoice item
            metadata: Additional metadata for the invoice item
            
        Returns:
            Response from the Billing API
            
        Raises:
            HTTPException: If the Billing API request fails
        """
        try:
            url = f"{self.billing_api_url}/invoice-items"
            
            data = {
                "user_id": user_id,
                "amount": float(amount),
                "description": description,
                "type": item_type,
                "metadata": metadata or {}
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=data
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"Created invoice item for user {user_id}: "
                    f"{description} - {amount}"
                )
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Billing API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Billing API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Billing API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Billing API request failed: {str(e)}"
            )
    
    async def calculate_prorated_amount(self, plan_price: Decimal, days_used: int, 
                                       days_in_cycle: int) -> Decimal:
        """
        Calculate a prorated amount based on days used in a billing cycle.
        
        Args:
            plan_price: The full price of the plan
            days_used: Number of days used in the cycle
            days_in_cycle: Total number of days in the cycle
            
        Returns:
            Prorated amount
        """
        if days_in_cycle <= 0:
            return Decimal('0.00')
        
        # Calculate the daily rate
        daily_rate = plan_price / Decimal(days_in_cycle)
        
        # Calculate the prorated amount
        prorated_amount = daily_rate * Decimal(days_used)
        
        # Round to 2 decimal places
        return prorated_amount.quantize(Decimal('0.01'))
    
    async def handle_plan_change(self, user_id: int, previous_plan: Dict[str, Any], 
                                new_plan: Dict[str, Any], effective_date: datetime,
                                current_cycle_start: datetime, 
                                current_cycle_end: datetime) -> Dict[str, Any]:
        """
        Handle billing aspects of a plan change.
        
        Args:
            user_id: The ID of the user
            previous_plan: The previous tariff plan data
            new_plan: The new tariff plan data
            effective_date: The effective date of the change
            current_cycle_start: Start date of the current billing cycle
            current_cycle_end: End date of the current billing cycle
            
        Returns:
            Dictionary with prorated credit and charge
            
        Raises:
            HTTPException: If the Billing API request fails
        """
        try:
            # Calculate days in the billing cycle
            days_in_cycle = (current_cycle_end - current_cycle_start).days
            if days_in_cycle <= 0:
                days_in_cycle = 30  # Default to 30 days if calculation is invalid
            
            # Calculate days used in the current cycle
            days_used = (effective_date - current_cycle_start).days
            if days_used < 0:
                days_used = 0
            elif days_used > days_in_cycle:
                days_used = days_in_cycle
            
            # Calculate days remaining in the cycle
            days_remaining = days_in_cycle - days_used
            
            # Calculate prorated credit for the previous plan
            previous_price = Decimal(str(previous_plan.get("price", 0)))
            prorated_credit = await self.calculate_prorated_amount(
                previous_price, days_remaining, days_in_cycle
            )
            
            # Calculate prorated charge for the new plan
            new_price = Decimal(str(new_plan.get("price", 0)))
            prorated_charge = await self.calculate_prorated_amount(
                new_price, days_remaining, days_in_cycle
            )
            
            # Create invoice items
            if prorated_credit > Decimal('0.00'):
                await self.create_invoice_item(
                    user_id=user_id,
                    amount=-prorated_credit,  # Negative amount for credit
                    description=f"Prorated credit for {previous_plan.get('name')} plan",
                    item_type="tariff_plan_credit",
                    metadata={
                        "previous_plan_id": previous_plan.get("id"),
                        "previous_plan_name": previous_plan.get("name"),
                        "days_remaining": days_remaining,
                        "days_in_cycle": days_in_cycle,
                        "effective_date": effective_date.isoformat()
                    }
                )
            
            if prorated_charge > Decimal('0.00'):
                await self.create_invoice_item(
                    user_id=user_id,
                    amount=prorated_charge,
                    description=f"Prorated charge for {new_plan.get('name')} plan",
                    item_type="tariff_plan_charge",
                    metadata={
                        "new_plan_id": new_plan.get("id"),
                        "new_plan_name": new_plan.get("name"),
                        "days_remaining": days_remaining,
                        "days_in_cycle": days_in_cycle,
                        "effective_date": effective_date.isoformat()
                    }
                )
            
            return {
                "prorated_credit": float(prorated_credit),
                "prorated_charge": float(prorated_charge),
                "days_used": days_used,
                "days_remaining": days_remaining,
                "days_in_cycle": days_in_cycle
            }
        except Exception as e:
            logger.error(f"Failed to handle plan change billing: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to handle plan change billing: {str(e)}"
            )
    
    async def charge_overage_fee(self, user_id: int, plan_name: str, 
                               overage_mb: int, rate_per_mb: Decimal) -> Dict[str, Any]:
        """
        Charge an overage fee for exceeding data cap.
        
        Args:
            user_id: The ID of the user
            plan_name: The name of the tariff plan
            overage_mb: The amount of overage in MB
            rate_per_mb: The rate per MB for overage
            
        Returns:
            Response from the Billing API
            
        Raises:
            HTTPException: If the Billing API request fails
        """
        try:
            # Calculate the overage fee
            overage_fee = Decimal(overage_mb) * rate_per_mb
            
            # Round to 2 decimal places
            overage_fee = overage_fee.quantize(Decimal('0.01'))
            
            # Create an invoice item for the overage fee
            result = await self.create_invoice_item(
                user_id=user_id,
                amount=overage_fee,
                description=f"Data overage fee for {plan_name} plan ({overage_mb} MB)",
                item_type="data_overage",
                metadata={
                    "overage_mb": overage_mb,
                    "rate_per_mb": float(rate_per_mb),
                    "plan_name": plan_name
                }
            )
            
            logger.info(
                f"Charged overage fee for user {user_id}: "
                f"{overage_fee} for {overage_mb} MB overage"
            )
            
            return {
                "user_id": user_id,
                "overage_mb": overage_mb,
                "rate_per_mb": float(rate_per_mb),
                "overage_fee": float(overage_fee),
                "invoice_item_id": result.get("id")
            }
        except Exception as e:
            logger.error(f"Failed to charge overage fee: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to charge overage fee: {str(e)}"
            )
    
    async def get_user_billing_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get billing information for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            User's billing information
            
        Raises:
            HTTPException: If the Billing API request fails
        """
        try:
            url = f"{self.billing_api_url}/users/{user_id}/billing-info"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=self.headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Billing API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Billing API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Billing API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Billing API request failed: {str(e)}"
            )
    
    async def get_user_invoices(self, user_id: int, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent invoices for a user.
        
        Args:
            user_id: The ID of the user
            limit: Maximum number of invoices to return
            
        Returns:
            User's recent invoices
            
        Raises:
            HTTPException: If the Billing API request fails
        """
        try:
            url = f"{self.billing_api_url}/users/{user_id}/invoices"
            
            params = {
                "limit": limit
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Billing API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Billing API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Billing API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Billing API request failed: {str(e)}"
            )
    
    async def sync_billing_cycle(self, user_id: int, tariff_plan_id: int, 
                                cycle_start: datetime, cycle_end: datetime) -> Dict[str, Any]:
        """
        Synchronize the billing cycle with the tariff plan cycle.
        
        Args:
            user_id: The ID of the user
            tariff_plan_id: The ID of the tariff plan
            cycle_start: Start date of the billing cycle
            cycle_end: End date of the billing cycle
            
        Returns:
            Response from the Billing API
            
        Raises:
            HTTPException: If the Billing API request fails
        """
        try:
            url = f"{self.billing_api_url}/users/{user_id}/sync-billing-cycle"
            
            data = {
                "tariff_plan_id": tariff_plan_id,
                "cycle_start": cycle_start.isoformat(),
                "cycle_end": cycle_end.isoformat()
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=data
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"Synchronized billing cycle for user {user_id} with tariff plan {tariff_plan_id}: "
                    f"{cycle_start.isoformat()} to {cycle_end.isoformat()}"
                )
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Billing API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Billing API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Billing API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Billing API request failed: {str(e)}"
            )
    
    async def calculate_next_billing_date(self, current_date: datetime, 
                                        billing_cycle: str) -> datetime:
        """
        Calculate the next billing date based on the billing cycle.
        
        Args:
            current_date: The current date
            billing_cycle: The billing cycle (monthly, quarterly, etc.)
            
        Returns:
            Next billing date
        """
        if billing_cycle == "monthly":
            # Add one month
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)
        elif billing_cycle == "quarterly":
            # Add three months
            month = current_date.month + 3
            year = current_date.year
            if month > 12:
                month -= 12
                year += 1
            return current_date.replace(year=year, month=month)
        elif billing_cycle == "biannual":
            # Add six months
            month = current_date.month + 6
            year = current_date.year
            if month > 12:
                month -= 12
                year += 1
            return current_date.replace(year=year, month=month)
        elif billing_cycle == "annual":
            # Add one year
            return current_date.replace(year=current_date.year + 1)
        else:
            # Default to monthly
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)


# Create a singleton instance
billing_integration = BillingIntegration()
