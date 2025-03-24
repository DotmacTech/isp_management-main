"""
User resource manager for the UNMS API.
"""
from typing import Dict, List, Any, Optional
import logging

from ..core import UNMSAPI
from ..exceptions import ValidationError, ResourceNotFoundError
from ..utils import validate_params, add_resource_links, add_collection_links

logger = logging.getLogger('unms')


class UserManager:
    """
    Manager for UNMS users.
    
    This class provides methods for managing users in UNMS.
    """
    
    def __init__(self, client):
        """
        Initialize the user manager.
        
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
        role: Optional[str] = None,
        status: Optional[str] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get all users.
        
        Args:
            page (int, optional): Page number. Defaults to 1.
            limit (int, optional): Items per page. Defaults to 100.
            sort (Optional[str], optional): Sort field. Defaults to None.
            order (Optional[str], optional): Sort order ('asc' or 'desc'). Defaults to None.
            search (Optional[str], optional): Search query. Defaults to None.
            role (Optional[str], optional): Filter by role. Defaults to None.
            status (Optional[str], optional): Filter by status. Defaults to None.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: List of users.
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
        
        if role:
            params['role'] = role
        
        if status:
            params['status'] = status
        
        return self.client.get('users', params=params, skip_cache=skip_cache)
    
    def get_by_id(self, user_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get a user by ID.
        
        Args:
            user_id (str): User ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: User details.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        return self.client.get(f'users/{user_id}', skip_cache=skip_cache)
    
    def get_current(self, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get the current user.
        
        Args:
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: Current user details.
        """
        return self.client.get('users/me', skip_cache=skip_cache)
    
    def create(
        self,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: str = 'viewer',
        phone: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            username (str): Username.
            email (str): Email address.
            password (str): Password.
            first_name (Optional[str], optional): First name. Defaults to None.
            last_name (Optional[str], optional): Last name. Defaults to None.
            role (str, optional): User role. Defaults to 'viewer'.
            phone (Optional[str], optional): Phone number. Defaults to None.
            note (Optional[str], optional): User note. Defaults to None.
            
        Returns:
            Dict[str, Any]: Created user.
        """
        if not username:
            raise ValueError("Username is required")
        
        if not email:
            raise ValueError("Email is required")
        
        if not password:
            raise ValueError("Password is required")
        
        data = {
            'username': username,
            'email': email,
            'password': password,
            'role': role
        }
        
        if first_name:
            data['firstName'] = first_name
        
        if last_name:
            data['lastName'] = last_name
        
        if phone:
            data['phone'] = phone
        
        if note:
            data['note'] = note
        
        return self.client.post('users', json_data=data)
    
    def update(
        self,
        user_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: Optional[str] = None,
        phone: Optional[str] = None,
        note: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a user.
        
        Args:
            user_id (str): User ID.
            username (Optional[str], optional): Username. Defaults to None.
            email (Optional[str], optional): Email address. Defaults to None.
            password (Optional[str], optional): Password. Defaults to None.
            first_name (Optional[str], optional): First name. Defaults to None.
            last_name (Optional[str], optional): Last name. Defaults to None.
            role (Optional[str], optional): User role. Defaults to None.
            phone (Optional[str], optional): Phone number. Defaults to None.
            note (Optional[str], optional): User note. Defaults to None.
            status (Optional[str], optional): User status. Defaults to None.
            
        Returns:
            Dict[str, Any]: Updated user.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        data = {}
        
        if username:
            data['username'] = username
        
        if email:
            data['email'] = email
        
        if password:
            data['password'] = password
        
        if first_name:
            data['firstName'] = first_name
        
        if last_name:
            data['lastName'] = last_name
        
        if role:
            data['role'] = role
        
        if phone:
            data['phone'] = phone
        
        if note:
            data['note'] = note
        
        if status:
            data['status'] = status
        
        if not data:
            raise ValueError("At least one field must be updated")
        
        return self.client.put(f'users/{user_id}', json_data=data)
    
    def delete(self, user_id: str) -> Dict[str, Any]:
        """
        Delete a user.
        
        Args:
            user_id (str): User ID.
            
        Returns:
            Dict[str, Any]: Response data.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        return self.client.delete(f'users/{user_id}')
    
    def update_password(self, user_id: str, password: str) -> Dict[str, Any]:
        """
        Update a user's password.
        
        Args:
            user_id (str): User ID.
            password (str): New password.
            
        Returns:
            Dict[str, Any]: Response data.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        if not password:
            raise ValueError("Password is required")
        
        return self.client.put(f'users/{user_id}/password', json_data={'password': password})
    
    def update_current_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        Update the current user's password.
        
        Args:
            current_password (str): Current password.
            new_password (str): New password.
            
        Returns:
            Dict[str, Any]: Response data.
        """
        if not current_password:
            raise ValueError("Current password is required")
        
        if not new_password:
            raise ValueError("New password is required")
        
        return self.client.put('users/me/password', json_data={
            'currentPassword': current_password,
            'newPassword': new_password
        })
    
    def get_permissions(self, user_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get a user's permissions.
        
        Args:
            user_id (str): User ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: User permissions.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        return self.client.get(f'users/{user_id}/permissions', skip_cache=skip_cache)
    
    def update_permissions(self, user_id: str, permissions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user's permissions.
        
        Args:
            user_id (str): User ID.
            permissions (Dict[str, Any]): Permissions data.
            
        Returns:
            Dict[str, Any]: Updated permissions.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        if not permissions:
            raise ValueError("Permissions data is required")
        
        return self.client.put(f'users/{user_id}/permissions', json_data=permissions)


class AsyncUserManager:
    """
    Asynchronous manager for UNMS users.
    
    This class provides asynchronous methods for managing users in UNMS.
    """
    
    def __init__(self, client):
        """
        Initialize the asynchronous user manager.
        
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
        role: Optional[str] = None,
        status: Optional[str] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get all users.
        
        Args:
            page (int, optional): Page number. Defaults to 1.
            limit (int, optional): Items per page. Defaults to 100.
            sort (Optional[str], optional): Sort field. Defaults to None.
            order (Optional[str], optional): Sort order ('asc' or 'desc'). Defaults to None.
            search (Optional[str], optional): Search query. Defaults to None.
            role (Optional[str], optional): Filter by role. Defaults to None.
            status (Optional[str], optional): Filter by status. Defaults to None.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: List of users.
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
        
        if role:
            params['role'] = role
        
        if status:
            params['status'] = status
        
        return await self.client.get('users', params=params, skip_cache=skip_cache)
    
    async def get_by_id(self, user_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get a user by ID.
        
        Args:
            user_id (str): User ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: User details.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        return await self.client.get(f'users/{user_id}', skip_cache=skip_cache)
    
    async def get_current(self, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get the current user.
        
        Args:
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: Current user details.
        """
        return await self.client.get('users/me', skip_cache=skip_cache)
    
    async def create(
        self,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: str = 'viewer',
        phone: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            username (str): Username.
            email (str): Email address.
            password (str): Password.
            first_name (Optional[str], optional): First name. Defaults to None.
            last_name (Optional[str], optional): Last name. Defaults to None.
            role (str, optional): User role. Defaults to 'viewer'.
            phone (Optional[str], optional): Phone number. Defaults to None.
            note (Optional[str], optional): User note. Defaults to None.
            
        Returns:
            Dict[str, Any]: Created user.
        """
        if not username:
            raise ValueError("Username is required")
        
        if not email:
            raise ValueError("Email is required")
        
        if not password:
            raise ValueError("Password is required")
        
        data = {
            'username': username,
            'email': email,
            'password': password,
            'role': role
        }
        
        if first_name:
            data['firstName'] = first_name
        
        if last_name:
            data['lastName'] = last_name
        
        if phone:
            data['phone'] = phone
        
        if note:
            data['note'] = note
        
        return await self.client.post('users', json_data=data)
    
    async def update(
        self,
        user_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: Optional[str] = None,
        phone: Optional[str] = None,
        note: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a user.
        
        Args:
            user_id (str): User ID.
            username (Optional[str], optional): Username. Defaults to None.
            email (Optional[str], optional): Email address. Defaults to None.
            password (Optional[str], optional): Password. Defaults to None.
            first_name (Optional[str], optional): First name. Defaults to None.
            last_name (Optional[str], optional): Last name. Defaults to None.
            role (Optional[str], optional): User role. Defaults to None.
            phone (Optional[str], optional): Phone number. Defaults to None.
            note (Optional[str], optional): User note. Defaults to None.
            status (Optional[str], optional): User status. Defaults to None.
            
        Returns:
            Dict[str, Any]: Updated user.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        data = {}
        
        if username:
            data['username'] = username
        
        if email:
            data['email'] = email
        
        if password:
            data['password'] = password
        
        if first_name:
            data['firstName'] = first_name
        
        if last_name:
            data['lastName'] = last_name
        
        if role:
            data['role'] = role
        
        if phone:
            data['phone'] = phone
        
        if note:
            data['note'] = note
        
        if status:
            data['status'] = status
        
        if not data:
            raise ValueError("At least one field must be updated")
        
        return await self.client.put(f'users/{user_id}', json_data=data)
    
    async def delete(self, user_id: str) -> Dict[str, Any]:
        """
        Delete a user.
        
        Args:
            user_id (str): User ID.
            
        Returns:
            Dict[str, Any]: Response data.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        return await self.client.delete(f'users/{user_id}')
    
    async def update_password(self, user_id: str, password: str) -> Dict[str, Any]:
        """
        Update a user's password.
        
        Args:
            user_id (str): User ID.
            password (str): New password.
            
        Returns:
            Dict[str, Any]: Response data.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        if not password:
            raise ValueError("Password is required")
        
        return await self.client.put(f'users/{user_id}/password', json_data={'password': password})
    
    async def update_current_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        Update the current user's password.
        
        Args:
            current_password (str): Current password.
            new_password (str): New password.
            
        Returns:
            Dict[str, Any]: Response data.
        """
        if not current_password:
            raise ValueError("Current password is required")
        
        if not new_password:
            raise ValueError("New password is required")
        
        return await self.client.put('users/me/password', json_data={
            'currentPassword': current_password,
            'newPassword': new_password
        })
    
    async def get_permissions(self, user_id: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Get a user's permissions.
        
        Args:
            user_id (str): User ID.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Dict[str, Any]: User permissions.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        return await self.client.get(f'users/{user_id}/permissions', skip_cache=skip_cache)
    
    async def update_permissions(self, user_id: str, permissions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user's permissions.
        
        Args:
            user_id (str): User ID.
            permissions (Dict[str, Any]): Permissions data.
            
        Returns:
            Dict[str, Any]: Updated permissions.
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        if not permissions:
            raise ValueError("Permissions data is required")
        
        return await self.client.put(f'users/{user_id}/permissions', json_data=permissions)


def init_user_managers(api_client):
    """
    Initialize user managers for an API client.
    
    Args:
        api_client: UNMS API client.
    """
    from ..core import AsyncUNMSAPI
    
    if hasattr(api_client, 'users'):
        logger.debug("User managers already initialized")
        return
    
    if isinstance(api_client, AsyncUNMSAPI):
        api_client.users = AsyncUserManager(api_client)
    else:
        api_client.users = UserManager(api_client)
