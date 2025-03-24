"""
UNMS service implementation.

This service provides a high-level interface for interacting with UNMS APIs.
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.config import settings
from ..core import UNMSAPI, AsyncUNMSAPI

logger = logging.getLogger('unms')


class UNMSService:
    """
    Service for interacting with UNMS/UISP APIs and integrating with the ISP management system.
    
    This service provides high-level methods for accessing UNMS functionality
    and implements business logic for integrating with the rest of the system.
    """
    
    def __init__(self, db: Session = Depends(get_db)):
        """
        Initialize the UNMS service.
        
        Args:
            db: Database session
        """
        self.db = db
        self._sync_client = None
        self._async_client = None
    
    @property
    def client(self) -> UNMSAPI:
        """
        Get the synchronous UNMS API client.
        
        Returns:
            UNMSAPI: Synchronous API client
        """
        if self._sync_client is None:
            try:
                # Get configuration from env or DB
                base_url = settings.UNMS_API_URL
                username = settings.UNMS_API_USERNAME
                password = settings.UNMS_API_PASSWORD
                
                self._sync_client = UNMSAPI(
                    base_url=base_url,
                    username=username,
                    password=password,
                    ssl_verify=settings.UNMS_API_SSL_VERIFY
                )
                
                # Initialize resource managers
                from ..resources import DeviceManager, SiteManager, UserManager
                self._sync_client.devices = DeviceManager(self._sync_client)
                self._sync_client.sites = SiteManager(self._sync_client)
                self._sync_client.users = UserManager(self._sync_client)
                
            except Exception as e:
                logger.error(f"Failed to initialize UNMS API client: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="UNMS service unavailable"
                )
        
        return self._sync_client
    
    @property
    def async_client(self) -> AsyncUNMSAPI:
        """
        Get the asynchronous UNMS API client.
        
        Returns:
            AsyncUNMSAPI: Asynchronous API client
        """
        if self._async_client is None:
            try:
                # Get configuration from env or DB
                base_url = settings.UNMS_API_URL
                username = settings.UNMS_API_USERNAME
                password = settings.UNMS_API_PASSWORD
                
                self._async_client = AsyncUNMSAPI(
                    base_url=base_url,
                    username=username,
                    password=password,
                    ssl_verify=settings.UNMS_API_SSL_VERIFY
                )
                
                # Initialize resource managers
                from ..resources import DeviceManager, SiteManager, UserManager
                self._async_client.devices = DeviceManager(self._async_client)
                self._async_client.sites = SiteManager(self._async_client)
                self._async_client.users = UserManager(self._async_client)
                
            except Exception as e:
                logger.error(f"Failed to initialize async UNMS API client: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="UNMS service unavailable"
                )
        
        return self._async_client
    
    async def get_devices(self, site_id: Optional[str] = None, 
                         status: Optional[str] = None,
                         limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of devices from UNMS.
        
        Args:
            site_id: Filter devices by site ID
            status: Filter devices by status
            limit: Maximum number of results to return
            offset: Result offset for pagination
            
        Returns:
            List of devices
        """
        try:
            params = {}
            if site_id:
                params['site'] = site_id
            if status:
                params['status'] = status
            
            client = self.async_client
            devices = await client.devices.list(limit=limit, offset=offset, **params)
            return devices
        except Exception as e:
            logger.error(f"Error fetching devices from UNMS: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error retrieving devices from UNMS"
            )
    
    async def get_sites(self, parent_id: Optional[str] = None,
                       limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of sites from UNMS.
        
        Args:
            parent_id: Filter sites by parent site ID
            limit: Maximum number of results to return
            offset: Result offset for pagination
            
        Returns:
            List of sites
        """
        try:
            params = {}
            if parent_id:
                params['parent'] = parent_id
            
            client = self.async_client
            sites = await client.sites.list(limit=limit, offset=offset, **params)
            return sites
        except Exception as e:
            logger.error(f"Error fetching sites from UNMS: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error retrieving sites from UNMS"
            )
    
    async def get_device(self, device_id: str) -> Dict[str, Any]:
        """
        Get a specific device from UNMS.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device details
        """
        try:
            client = self.async_client
            device = await client.devices.get(device_id)
            return device
        except Exception as e:
            logger.error(f"Error fetching device {device_id} from UNMS: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
    
    async def get_site(self, site_id: str) -> Dict[str, Any]:
        """
        Get a specific site from UNMS.
        
        Args:
            site_id: Site ID
            
        Returns:
            Site details
        """
        try:
            client = self.async_client
            site = await client.sites.get(site_id)
            return site
        except Exception as e:
            logger.error(f"Error fetching site {site_id} from UNMS: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site {site_id} not found"
            )
