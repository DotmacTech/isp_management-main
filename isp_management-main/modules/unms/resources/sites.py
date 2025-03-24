"""
Site resource manager for the UNMS API.
"""
from typing import Dict, List, Any, Optional

from ..core import UNMSAPI

class SiteManager:
    """
    Manager for UNMS sites.
    
    This class provides methods for managing sites in UNMS.
    """
    
    def __init__(self, client):
        """
        Initialize the site manager.
        
        Args:
            client: UNMS API client.
        """
        self.client = client
    
    def get_all(
        self,
        page: int = 1,
        limit: int = 100,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        include_deleted: bool = False,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get all sites.
        
        Args:
            page (int, optional): Page number. Defaults to 1.
            limit (int, optional): Items per page. Defaults to 100.
            sort (Optional[str], optional): Sort field. Defaults to None.
            order (Optional[str], optional): Sort order ('asc' or 'desc'). Defaults to None.
            search (Optional[str], optional): Search query. Defaults to None.
            status (Optional[str], optional): Filter by status. Defaults to None.
            include_deleted (bool, optional): Whether to include deleted sites. Defaults to False.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: List of sites.
        """
        params = {
            'page': page,
            'limit': limit
        }
        
        if sort:
            params['sort'] = sort
        
        if order:
            params['order'] = order
        
        if search:
            params['search'] = search
        
        if status:
            params['status'] = status
        
        if include_deleted:
            params['includeDeleted'] = 'true'
        
        return self.client.get('sites', params=params, skip_cache=skip_cache)
    
    def get_by_id(self, site_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get a site by ID.
        
        Args:
            site_id (str): Site ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: Site details.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        return self.client.get(f'sites/{site_id}', skip_cache=skip_cache)
    
    def create(self, name: str, location: Optional[Dict[str, Any]] = None, 
              description: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new site.
        
        Args:
            name (str): Site name.
            location (Optional[Dict[str, Any]], optional): Site location. Defaults to None.
            description (Optional[str], optional): Site description. Defaults to None.
            attributes (Optional[Dict[str, Any]], optional): Site attributes. Defaults to None.
            
        Returns:
            Dict[str, Any]: Created site.
        """
        if not name:
            raise ValueError("Site name is required")
        
        data = {
            'name': name
        }
        
        if location:
            data['location'] = location
        
        if description:
            data['description'] = description
        
        if attributes:
            data['attributes'] = attributes
        
        return self.client.post('sites', json_data=data)
    
    def update(self, site_id: str, name: Optional[str] = None, 
              location: Optional[Dict[str, Any]] = None, description: Optional[str] = None, 
              attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update a site.
        
        Args:
            site_id (str): Site ID.
            name (Optional[str], optional): Site name. Defaults to None.
            location (Optional[Dict[str, Any]], optional): Site location. Defaults to None.
            description (Optional[str], optional): Site description. Defaults to None.
            attributes (Optional[Dict[str, Any]], optional): Site attributes. Defaults to None.
            
        Returns:
            Dict[str, Any]: Updated site.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        data = {}
        
        if name:
            data['name'] = name
        
        if location:
            data['location'] = location
        
        if description:
            data['description'] = description
        
        if attributes:
            data['attributes'] = attributes
        
        if not data:
            raise ValueError("At least one field must be updated")
        
        return self.client.put(f'sites/{site_id}', json_data=data)
    
    def delete(self, site_id: str) -> Dict[str, Any]:
        """
        Delete a site.
        
        Args:
            site_id (str): Site ID.
            
        Returns:
            Dict[str, Any]: Response data.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        return self.client.delete(f'sites/{site_id}')
    
    def get_devices(self, site_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get devices for a site.
        
        Args:
            site_id (str): Site ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: List of devices.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        return self.client.get(f'sites/{site_id}/devices', skip_cache=skip_cache)
    
    def get_outages(self, site_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get outages for a site.
        
        Args:
            site_id (str): Site ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: List of outages.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        return self.client.get(f'sites/{site_id}/outages', skip_cache=skip_cache)
    
    def get_statistics(self, site_id: str, interval: str = 'day', skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get statistics for a site.
        
        Args:
            site_id (str): Site ID.
            interval (str, optional): Statistics interval ('hour', 'day', 'week', 'month'). Defaults to 'day'.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: Site statistics.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        valid_intervals = ['hour', 'day', 'week', 'month']
        if interval not in valid_intervals:
            raise ValueError(f"Invalid interval. Must be one of {', '.join(valid_intervals)}")
        
        return self.client.get(f'sites/{site_id}/statistics', params={'interval': interval}, skip_cache=skip_cache)


class AsyncSiteManager:
    """
    Asynchronous manager for UNMS sites.
    
    This class provides asynchronous methods for managing sites in UNMS.
    """
    
    def __init__(self, client):
        """
        Initialize the asynchronous site manager.
        
        Args:
            client: Asynchronous UNMS API client.
        """
        self.client = client
    
    async def get_all(
        self,
        page: int = 1,
        limit: int = 100,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        include_deleted: bool = False,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get all sites.
        
        Args:
            page (int, optional): Page number. Defaults to 1.
            limit (int, optional): Items per page. Defaults to 100.
            sort (Optional[str], optional): Sort field. Defaults to None.
            order (Optional[str], optional): Sort order ('asc' or 'desc'). Defaults to None.
            search (Optional[str], optional): Search query. Defaults to None.
            status (Optional[str], optional): Filter by status. Defaults to None.
            include_deleted (bool, optional): Whether to include deleted sites. Defaults to False.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: List of sites.
        """
        params = {
            'page': page,
            'limit': limit
        }
        
        if sort:
            params['sort'] = sort
        
        if order:
            params['order'] = order
        
        if search:
            params['search'] = search
        
        if status:
            params['status'] = status
        
        if include_deleted:
            params['includeDeleted'] = 'true'
        
        return await self.client.get('sites', params=params, skip_cache=skip_cache)
    
    async def get_by_id(self, site_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get a site by ID.
        
        Args:
            site_id (str): Site ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: Site details.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        return await self.client.get(f'sites/{site_id}', skip_cache=skip_cache)
    
    async def create(self, name: str, location: Optional[Dict[str, Any]] = None, 
                   description: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new site.
        
        Args:
            name (str): Site name.
            location (Optional[Dict[str, Any]], optional): Site location. Defaults to None.
            description (Optional[str], optional): Site description. Defaults to None.
            attributes (Optional[Dict[str, Any]], optional): Site attributes. Defaults to None.
            
        Returns:
            Dict[str, Any]: Created site.
        """
        if not name:
            raise ValueError("Site name is required")
        
        data = {
            'name': name
        }
        
        if location:
            data['location'] = location
        
        if description:
            data['description'] = description
        
        if attributes:
            data['attributes'] = attributes
        
        return await self.client.post('sites', json_data=data)
    
    async def update(self, site_id: str, name: Optional[str] = None, 
                   location: Optional[Dict[str, Any]] = None, description: Optional[str] = None, 
                   attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update a site.
        
        Args:
            site_id (str): Site ID.
            name (Optional[str], optional): Site name. Defaults to None.
            location (Optional[Dict[str, Any]], optional): Site location. Defaults to None.
            description (Optional[str], optional): Site description. Defaults to None.
            attributes (Optional[Dict[str, Any]], optional): Site attributes. Defaults to None.
            
        Returns:
            Dict[str, Any]: Updated site.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        data = {}
        
        if name:
            data['name'] = name
        
        if location:
            data['location'] = location
        
        if description:
            data['description'] = description
        
        if attributes:
            data['attributes'] = attributes
        
        if not data:
            raise ValueError("At least one field must be updated")
        
        return await self.client.put(f'sites/{site_id}', json_data=data)
    
    async def delete(self, site_id: str) -> Dict[str, Any]:
        """
        Delete a site.
        
        Args:
            site_id (str): Site ID.
            
        Returns:
            Dict[str, Any]: Response data.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        return await self.client.delete(f'sites/{site_id}')
    
    async def get_devices(self, site_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get devices for a site.
        
        Args:
            site_id (str): Site ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: List of devices.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        return await self.client.get(f'sites/{site_id}/devices', skip_cache=skip_cache)
    
    async def get_outages(self, site_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get outages for a site.
        
        Args:
            site_id (str): Site ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: List of outages.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        return await self.client.get(f'sites/{site_id}/outages', skip_cache=skip_cache)
    
    async def get_statistics(self, site_id: str, interval: str = 'day', skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get statistics for a site.
        
        Args:
            site_id (str): Site ID.
            interval (str, optional): Statistics interval ('hour', 'day', 'week', 'month'). Defaults to 'day'.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: Site statistics.
        """
        if not site_id:
            raise ValueError("Site ID is required")
        
        valid_intervals = ['hour', 'day', 'week', 'month']
        if interval not in valid_intervals:
            raise ValueError(f"Invalid interval. Must be one of {', '.join(valid_intervals)}")
        
        return await self.client.get(f'sites/{site_id}/statistics', params={'interval': interval}, skip_cache=skip_cache)


def init_site_managers(api_client):
    """
    Initialize site managers for an API client.
    
    Args:
        api_client: UNMS API client.
    """
    from ..async_client import AsyncUNMSAPI
    
    if hasattr(api_client, 'sites'):
        logger.debug("Site managers already initialized")
        return
    
    if isinstance(api_client, AsyncUNMSAPI):
        api_client.sites = AsyncSiteManager(api_client)
    else:
        api_client.sites = SiteManager(api_client)
