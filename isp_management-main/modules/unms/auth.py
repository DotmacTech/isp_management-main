"""
Authentication handling for the UNMS API client.
"""
import logging
import time
from typing import Optional, Dict, Any

from .exceptions import AuthenticationError, TokenExpiredError

logger = logging.getLogger('unms_api')


class AuthManager:
    """
    Authentication manager for UNMS API.
    
    This class handles authentication token management and refresh.
    """
    
    def __init__(self, base_url: str, auto_reconnect: bool = True, token_refresh: bool = True):
        """
        Initialize the authentication manager.
        
        Args:
            base_url (str): Base URL of the UNMS API.
            auto_reconnect (bool, optional): Whether to automatically reconnect on token expiration. Defaults to True.
            token_refresh (bool, optional): Whether to refresh the token when it expires. Defaults to True.
        """
        self.base_url = base_url
        self.auto_reconnect = auto_reconnect
        self.token_refresh = token_refresh
        self._token = None
        self._token_expiry = None
        self._refresh_token = None
    
    def has_token(self) -> bool:
        """
        Check if a token is available.
        
        Returns:
            bool: Whether a token is available.
        """
        return self._token is not None
    
    def get_token(self) -> Optional[str]:
        """
        Get the current authentication token.
        
        Returns:
            Optional[str]: Authentication token.
        """
        return self._token
    
    def set_token(self, token: str, expiry: Optional[int] = None, refresh_token: Optional[str] = None) -> None:
        """
        Set the authentication token.
        
        Args:
            token (str): Authentication token.
            expiry (Optional[int], optional): Token expiry timestamp. Defaults to None.
            refresh_token (Optional[str], optional): Refresh token. Defaults to None.
        """
        self._token = token
        self._token_expiry = expiry
        self._refresh_token = refresh_token
        logger.debug("Authentication token set")
    
    def clear_token(self) -> None:
        """
        Clear the authentication token.
        """
        self._token = None
        self._token_expiry = None
        self._refresh_token = None
        logger.debug("Authentication token cleared")
    
    def is_token_expired(self) -> bool:
        """
        Check if the token is expired.
        
        Returns:
            bool: Whether the token is expired.
        """
        if not self._token or not self._token_expiry:
            return True
        
        # Add a 30-second buffer to ensure we don't use a token that's about to expire
        return time.time() + 30 >= self._token_expiry
    
    def can_refresh_token(self) -> bool:
        """
        Check if the token can be refreshed.
        
        Returns:
            bool: Whether the token can be refreshed.
        """
        return self.token_refresh and self._refresh_token is not None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dict[str, str]: Authentication headers.
        """
        if not self._token:
            return {}
        
        return {
            'Authorization': f'Bearer {self._token}'
        }
    
    def login(self, username: str, password: str, session) -> bool:
        """
        Log in to the UNMS API.
        
        Args:
            username (str): Username.
            password (str): Password.
            session: Requests session.
            
        Returns:
            bool: Whether login was successful.
            
        Raises:
            AuthenticationError: If authentication fails.
        """
        data = {
            'username': username,
            'password': password
        }
        
        try:
            response = session.post(f"{self.base_url}/auth/login", json=data)
            
            if response.status_code != 200:
                logger.error(f"Authentication failed: {response.status_code} {response.reason}")
                raise AuthenticationError(f"Authentication failed: {response.status_code} {response.reason}")
            
            auth_data = response.json()
            
            # Extract token and expiry
            token = auth_data.get('token')
            expiry = auth_data.get('expires')
            refresh_token = auth_data.get('refreshToken')
            
            if not token:
                logger.error("Authentication failed: No token in response")
                raise AuthenticationError("Authentication failed: No token in response")
            
            self.set_token(token, expiry, refresh_token)
            logger.info(f"Successfully authenticated as {username}")
            
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")
    
    def logout(self, session) -> bool:
        """
        Log out from the UNMS API.
        
        Args:
            session: Requests session.
            
        Returns:
            bool: Whether logout was successful.
        """
        if not self._token:
            logger.warning("No active session to log out from")
            return True
        
        try:
            headers = self.get_auth_headers()
            response = session.post(f"{self.base_url}/auth/logout", headers=headers)
            
            # Clear token regardless of response
            self.clear_token()
            
            if response.status_code not in [200, 204]:
                logger.warning(f"Logout returned unexpected status: {response.status_code} {response.reason}")
                return False
            
            logger.info("Successfully logged out")
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            self.clear_token()  # Still clear token on error
            return False
    
    def refresh_token(self, session) -> bool:
        """
        Refresh the authentication token.
        
        Args:
            session: Requests session.
            
        Returns:
            bool: Whether token refresh was successful.
            
        Raises:
            TokenExpiredError: If token refresh fails.
        """
        if not self._refresh_token:
            logger.error("Cannot refresh token: No refresh token available")
            raise TokenExpiredError("Cannot refresh token: No refresh token available")
        
        try:
            data = {
                'refreshToken': self._refresh_token
            }
            
            response = session.post(f"{self.base_url}/auth/refresh", json=data)
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code} {response.reason}")
                raise TokenExpiredError(f"Token refresh failed: {response.status_code} {response.reason}")
            
            auth_data = response.json()
            
            # Extract token and expiry
            token = auth_data.get('token')
            expiry = auth_data.get('expires')
            refresh_token = auth_data.get('refreshToken')
            
            if not token:
                logger.error("Token refresh failed: No token in response")
                raise TokenExpiredError("Token refresh failed: No token in response")
            
            self.set_token(token, expiry, refresh_token)
            logger.info("Successfully refreshed authentication token")
            
            return True
            
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise TokenExpiredError(f"Token refresh failed: {str(e)}")


class AuthHandlerMixin:
    """
    Mixin for handling authentication in API clients.
    """
    
    def login(self, username: str, password: str) -> bool:
        """
        Log in to the UNMS API.
        
        Args:
            username (str): Username.
            password (str): Password.
            
        Returns:
            bool: Whether login was successful.
        """
        return self.auth_manager.login(username, password, self.session)
    
    def logout(self) -> bool:
        """
        Log out from the UNMS API.
        
        Returns:
            bool: Whether logout was successful.
        """
        return self.auth_manager.logout(self.session)
    
    def set_token(self, token: str, expiry: Optional[int] = None, refresh_token: Optional[str] = None) -> None:
        """
        Set the authentication token.
        
        Args:
            token (str): Authentication token.
            expiry (Optional[int], optional): Token expiry timestamp. Defaults to None.
            refresh_token (Optional[str], optional): Refresh token. Defaults to None.
        """
        self.auth_manager.set_token(token, expiry, refresh_token)
    
    def get_token(self) -> Optional[str]:
        """
        Get the current authentication token.
        
        Returns:
            Optional[str]: Authentication token.
        """
        return self.auth_manager.get_token()
