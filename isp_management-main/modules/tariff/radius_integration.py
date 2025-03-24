"""
RADIUS Integration for the Tariff Enforcement Module.

This module handles the integration between the Tariff Enforcement Module and the RADIUS
module, ensuring that tariff policies are properly enforced at the network level.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
import httpx
from fastapi import HTTPException

from backend_core.config import settings
from backend_core.logging import get_logger
from modules.tariff.monitoring import tariff_monitoring

# Configure logger
logger = get_logger(__name__)


class RadiusIntegration:
    """
    Class for integrating with the RADIUS module.
    
    This class provides methods for applying tariff policies to RADIUS,
    updating user bandwidth restrictions, and synchronizing policy changes.
    """
    
    def __init__(self):
        """Initialize the RadiusIntegration instance."""
        self.radius_api_url = settings.RADIUS_API_URL
        self.api_key = settings.RADIUS_API_KEY
        self.timeout = settings.RADIUS_API_TIMEOUT or 10.0
        
        # Default headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Source": "tariff-module"
        }
    
    async def apply_policy(self, username: str, policy_id: int) -> Dict[str, Any]:
        """
        Apply a RADIUS policy to a user.
        
        Args:
            username: The username of the user
            policy_id: The ID of the RADIUS policy to apply
            
        Returns:
            Response from the RADIUS API
            
        Raises:
            HTTPException: If the RADIUS API request fails
        """
        try:
            url = f"{self.radius_api_url}/users/{username}/policy"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={"policy_id": policy_id}
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Applied RADIUS policy {policy_id} to user {username}")
                tariff_monitoring.track_policy_action(
                    action_type="apply_radius_policy",
                    trigger_type="policy_change",
                    plan_name="N/A"  # Plan name not available in this context
                )
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"RADIUS API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"RADIUS API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"RADIUS API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"RADIUS API request failed: {str(e)}"
            )
    
    async def update_bandwidth_limits(self, username: str, download_speed: int, 
                                     upload_speed: int) -> Dict[str, Any]:
        """
        Update bandwidth limits for a user.
        
        Args:
            username: The username of the user
            download_speed: Download speed limit in Mbps
            upload_speed: Upload speed limit in Mbps
            
        Returns:
            Response from the RADIUS API
            
        Raises:
            HTTPException: If the RADIUS API request fails
        """
        try:
            url = f"{self.radius_api_url}/users/{username}/bandwidth"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    url,
                    headers=self.headers,
                    json={
                        "download_speed": download_speed,
                        "upload_speed": upload_speed
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"Updated bandwidth limits for user {username}: "
                    f"{download_speed}/{upload_speed} Mbps"
                )
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"RADIUS API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"RADIUS API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"RADIUS API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"RADIUS API request failed: {str(e)}"
            )
    
    async def throttle_user(self, username: str, download_speed: int, 
                           upload_speed: int) -> Dict[str, Any]:
        """
        Throttle a user's bandwidth.
        
        Args:
            username: The username of the user
            download_speed: Throttled download speed in Mbps
            upload_speed: Throttled upload speed in Mbps
            
        Returns:
            Response from the RADIUS API
            
        Raises:
            HTTPException: If the RADIUS API request fails
        """
        try:
            url = f"{self.radius_api_url}/users/{username}/throttle"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={
                        "download_speed": download_speed,
                        "upload_speed": upload_speed,
                        "reason": "Data cap exceeded"
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"Throttled user {username} to {download_speed}/{upload_speed} Mbps"
                )
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"RADIUS API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"RADIUS API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"RADIUS API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"RADIUS API request failed: {str(e)}"
            )
    
    async def unthrottle_user(self, username: str) -> Dict[str, Any]:
        """
        Remove throttling from a user.
        
        Args:
            username: The username of the user
            
        Returns:
            Response from the RADIUS API
            
        Raises:
            HTTPException: If the RADIUS API request fails
        """
        try:
            url = f"{self.radius_api_url}/users/{username}/unthrottle"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={}
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Unthrottled user {username}")
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"RADIUS API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"RADIUS API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"RADIUS API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"RADIUS API request failed: {str(e)}"
            )
    
    async def get_user_policy(self, username: str) -> Dict[str, Any]:
        """
        Get the current RADIUS policy for a user.
        
        Args:
            username: The username of the user
            
        Returns:
            Response from the RADIUS API with the user's policy
            
        Raises:
            HTTPException: If the RADIUS API request fails
        """
        try:
            url = f"{self.radius_api_url}/users/{username}/policy"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=self.headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"RADIUS API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"RADIUS API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"RADIUS API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"RADIUS API request failed: {str(e)}"
            )
    
    async def get_user_usage(self, username: str, start_date: str = None, 
                            end_date: str = None) -> Dict[str, Any]:
        """
        Get usage data for a user from RADIUS.
        
        Args:
            username: The username of the user
            start_date: Optional start date for filtering (ISO format)
            end_date: Optional end date for filtering (ISO format)
            
        Returns:
            Response from the RADIUS API with the user's usage data
            
        Raises:
            HTTPException: If the RADIUS API request fails
        """
        try:
            url = f"{self.radius_api_url}/users/{username}/usage"
            params = {}
            
            if start_date:
                params["start_date"] = start_date
            
            if end_date:
                params["end_date"] = end_date
            
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
            logger.error(f"RADIUS API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"RADIUS API error: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"RADIUS API request failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"RADIUS API request failed: {str(e)}"
            )
    
    async def sync_policy_with_tariff_plan(self, username: str, tariff_plan: Dict[str, Any], 
                                          is_throttled: bool = False) -> Dict[str, Any]:
        """
        Synchronize RADIUS policy with a user's tariff plan.
        
        Args:
            username: The username of the user
            tariff_plan: The tariff plan data
            is_throttled: Whether the user is currently throttled
            
        Returns:
            Response from the RADIUS API
            
        Raises:
            HTTPException: If the RADIUS API request fails
        """
        try:
            # Determine which policy to apply based on throttling status
            if is_throttled and tariff_plan.get("throttled_radius_policy_id"):
                policy_id = tariff_plan["throttled_radius_policy_id"]
                download_speed = tariff_plan.get("throttle_speed_download", 1)
                upload_speed = tariff_plan.get("throttle_speed_upload", 1)
            else:
                policy_id = tariff_plan["radius_policy_id"]
                download_speed = tariff_plan["download_speed"]
                upload_speed = tariff_plan["upload_speed"]
            
            # Apply the policy
            if policy_id:
                await self.apply_policy(username, policy_id)
            
            # Update bandwidth limits
            result = await self.update_bandwidth_limits(
                username, download_speed, upload_speed
            )
            
            logger.info(
                f"Synchronized RADIUS policy for user {username} with tariff plan "
                f"{tariff_plan.get('name', 'Unknown')}"
            )
            
            return result
        except Exception as e:
            logger.error(f"Failed to sync policy with tariff plan: {str(e)}")
            raise
    
    async def bulk_sync_policies(self, user_plans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronize RADIUS policies for multiple users.
        
        Args:
            user_plans: List of user tariff plans to sync
            
        Returns:
            Summary of the synchronization results
            
        Raises:
            HTTPException: If the RADIUS API request fails
        """
        results = {
            "total": len(user_plans),
            "successful": 0,
            "failed": 0,
            "failures": []
        }
        
        for user_plan in user_plans:
            try:
                username = user_plan.get("username")
                if not username:
                    results["failed"] += 1
                    results["failures"].append({
                        "user_id": user_plan.get("user_id"),
                        "error": "Username not provided"
                    })
                    continue
                
                await self.sync_policy_with_tariff_plan(
                    username,
                    user_plan.get("tariff_plan", {}),
                    user_plan.get("is_throttled", False)
                )
                
                results["successful"] += 1
            except Exception as e:
                results["failed"] += 1
                results["failures"].append({
                    "user_id": user_plan.get("user_id"),
                    "username": user_plan.get("username"),
                    "error": str(e)
                })
        
        logger.info(
            f"Bulk sync of RADIUS policies completed: "
            f"{results['successful']} successful, {results['failed']} failed"
        )
        
        return results


# Create a singleton instance
radius_integration = RadiusIntegration()
