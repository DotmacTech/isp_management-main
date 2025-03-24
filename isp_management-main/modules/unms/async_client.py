"""
Asynchronous UNMS API client implementation.
"""
import json
import logging
import aiohttp
import asyncio
from typing import Optional, Dict, List, Any, Union, Callable
from datetime import datetime
import time
import random
from contextlib import asynccontextmanager

from .exceptions import (
    UNMSAPIError, AuthenticationError, RateLimitError, 
    ConnectionError, ValidationError, TokenExpiredError
)
from .auth import AuthManager
from .cache import CacheManager
from .utils import generate_cache_key, validate_params, parse_rate_limit_headers
from .config import get_config

logger = logging.getLogger('unms_api')


class AsyncUNMSAPI:
    """
    Asynchronous UNMS API client.
    
    This class provides asynchronous methods for interacting with the UNMS API.
    """
    
    def __init__(
        self, 
        base_url: Optional[str] = None,
        api_version: Optional[str] = None,
        ssl_verify: Optional[bool] = None,
        ssl_cert: Optional[str] = None,
        timeout: Optional[int] = None,
        proxy: Optional[Dict[str, str]] = None,
        auto_reconnect: Optional[bool] = None,
        max_retries: Optional[int] = None,
        retry_backoff: Optional[float] = None,
        cache_enabled: Optional[bool] = None,
        cache_ttl: Optional[int] = None,
        redis_url: Optional[str] = None,
        log_level: Optional[int] = None,
        trace_requests: Optional[bool] = None,
        config_file: Optional[str] = None
    ):
        """
        Initialize the asynchronous UNMS API client.
        
        Args:
            base_url (Optional[str]): Base URL of the UNMS API. Defaults to None.
            api_version (Optional[str]): API version to use. Defaults to None.
            ssl_verify (Optional[bool]): Whether to verify SSL certificates. Defaults to None.
            ssl_cert (Optional[str]): Path to a custom SSL certificate. Defaults to None.
            timeout (Optional[int]): Request timeout in seconds. Defaults to None.
            proxy (Optional[Dict[str, str]]): Proxy configuration for requests. Defaults to None.
            auto_reconnect (Optional[bool]): Whether to automatically reconnect on token expiration. Defaults to None.
            max_retries (Optional[int]): Maximum number of retries for failed requests. Defaults to None.
            retry_backoff (Optional[float]): Backoff factor for retries. Defaults to None.
            cache_enabled (Optional[bool]): Whether to enable caching. Defaults to None.
            cache_ttl (Optional[int]): Default TTL for cached responses in seconds. Defaults to None.
            redis_url (Optional[str]): Redis URL for caching. Defaults to None.
            log_level (Optional[int]): Logging level. Defaults to None.
            trace_requests (Optional[bool]): Whether to log request and response details. Defaults to None.
            config_file (Optional[str]): Path to a configuration file. Defaults to None.
        """
        # Load configuration
        self.config = get_config(config_file)
        
        # Apply settings with precedence: constructor args > config file > defaults
        self.base_url = base_url or self.config.get('api', 'base_url')
        if not self.base_url:
            raise ValueError("Base URL must be provided")
        
        self.base_url = self.base_url.rstrip('/')
        self.api_version = api_version or self.config.get('api', 'api_version', 'v2.1')
        self.ssl_verify = ssl_verify if ssl_verify is not None else self.config.get('api', 'ssl_verify', True)
        self.ssl_cert = ssl_cert or self.config.get('api', 'ssl_cert')
        self.timeout = timeout or self.config.get('api', 'timeout', 30)
        self.proxy = proxy or self.config.get('api', 'proxies')
        self.auto_reconnect = auto_reconnect if auto_reconnect is not None else self.config.get('api', 'auto_reconnect', True)
        self.max_retries = max_retries or self.config.get('api', 'max_retries', 3)
        self.retry_backoff = retry_backoff or self.config.get('api', 'retry_backoff', 0.5)
        
        # Cache settings
        cache_enabled = cache_enabled if cache_enabled is not None else self.config.get('cache', 'enabled', False)
        cache_ttl = cache_ttl or self.config.get('cache', 'ttl', 300)
        redis_url = redis_url or self.config.get('cache', 'redis_url')
        
        # Logging settings
        self.trace_requests = trace_requests if trace_requests is not None else self.config.get('logging', 'trace_requests', False)
        log_level_name = self.config.get('logging', 'level', 'INFO').upper()
        if hasattr(logging, log_level_name):
            log_level = getattr(logging, log_level_name)
        
        if log_level:
            logger.setLevel(log_level)
        
        # Setup authentication manager
        self.auth_manager = AuthManager(
            base_url=self.base_url,
            auto_reconnect=self.auto_reconnect,
            token_refresh=self.config.get('auth', 'token_refresh', True)
        )
        
        # Setup cache manager
        self.cache_manager = CacheManager(
            enabled=cache_enabled,
            default_ttl=cache_ttl,
            redis_url=redis_url
        )
        
        # Setup session
        self._session = None
        
        # Initialize auth token if provided in config
        token = self.config.get('auth', 'token')
        if token:
            self.auth_manager.set_token(token)
            logger.info("Using authentication token from configuration")
        
        # Resource references will be set by the resource modules
        self.devices = None
        self.sites = None
        self.users = None
        self.logs = None
        self.outages = None
        self.tasks = None
        self.statistics = None
        self.backups = None
        self.firmwares = None
        self.discovery = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create an aiohttp session.
        
        Returns:
            aiohttp.ClientSession: Session object.
        """
        if self._session is None or self._session.closed:
            ssl_context = None
            if self.ssl_cert:
                import ssl
                ssl_context = ssl.create_default_context(cafile=self.ssl_cert)
            
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=aiohttp.TCPConnector(ssl=self.ssl_verify, ssl_context=ssl_context)
            )
        
        return self._session
    
    async def close(self) -> None:
        """
        Close the aiohttp session.
        """
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _get_endpoint_url(self, endpoint: str) -> str:
        """
        Build a full URL for an API endpoint.
        
        Args:
            endpoint (str): API endpoint path.
            
        Returns:
            str: Full URL for the endpoint.
        """
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        # Check if the endpoint already includes version
        if endpoint.startswith(f'v{self.api_version}') or endpoint.startswith(f'v{self.api_version}/'):
            return f"{self.base_url}/{endpoint}"
        else:
            return f"{self.base_url}/v{self.api_version}/{endpoint}"
    
    async def _with_retry(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func (Callable): Async function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
            
        Returns:
            Any: Function result.
            
        Raises:
            UNMSAPIError: After max retries or on unrecoverable error.
        """
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                if retries > 0:
                    # Exponential backoff with jitter
                    backoff = self.retry_backoff * (2 ** (retries - 1))
                    jitter = backoff * 0.2 * (2 * random.random() - 1)  # ±20% jitter
                    sleep_time = max(0, backoff + jitter)
                    logger.debug(f"Retry {retries}/{self.max_retries}, sleeping for {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                
                return await func(*args, **kwargs)
            
            except (ConnectionError, RateLimitError) as e:
                retries += 1
                last_error = e
                logger.warning(f"Recoverable error, retry {retries}/{self.max_retries}: {e}")
                
                if retries > self.max_retries:
                    break
                else:
                    continue
            
            except TokenExpiredError as e:
                if self.auto_reconnect and self.auth_manager.can_refresh_token():
                    logger.info("Token expired, attempting to refresh")
                    session = await self._get_session()
                    await self.auth_manager.refresh_token(session)
                    retries += 1
                    continue
                else:
                    raise
            
            except Exception as e:
                # Non-recoverable error
                logger.error(f"Non-recoverable error: {e}")
                raise
        
        # If we got here, we've exceeded max retries
        logger.error(f"Max retries ({self.max_retries}) exceeded")
        if last_error:
            raise last_error
        else:
            raise UNMSAPIError("Max retries exceeded")
    
    async def _handle_response(self, response: aiohttp.ClientResponse, expected_status: List[int] = None) -> Any:
        """
        Handle a response from the API.
        
        Args:
            response (aiohttp.ClientResponse): Response object.
            expected_status (List[int], optional): List of expected status codes. Defaults to None.
            
        Returns:
            Any: Response data.
            
        Raises:
            AuthenticationError: If authentication failed.
            RateLimitError: If rate limit was exceeded.
            ValidationError: If request validation failed.
            UNMSAPIError: For other API errors.
        """
        if expected_status is None:
            expected_status = [200]
        
        # Log request details if trace_requests is enabled
        if self.trace_requests:
            logger.debug(f"Request: {response.method} {response.url}")
            logger.debug(f"Response: {response.status} {response.reason}")
        
        # Check for rate limiting
        if response.status == 429:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = None
            
            raise RateLimitError(
                f"Rate limit exceeded. Retry after {retry_after} seconds if specified.",
                retry_after=retry_after
            )
        
        # Check for authentication errors
        if response.status == 401:
            # Check if token expired
            try:
                data = await response.json()
                if data.get('message') == 'Token expired':
                    raise TokenExpiredError("Authentication token has expired")
            except (json.JSONDecodeError, KeyError):
                pass
            
            raise AuthenticationError("Authentication failed")
        
        # Check for validation errors
        if response.status == 400:
            try:
                data = await response.json()
                message = data.get('message', 'Validation error')
                details = data.get('details', {})
                raise ValidationError(message, details=details)
            except json.JSONDecodeError:
                raise ValidationError("Request validation failed")
        
        # Check for other errors
        if response.status not in expected_status:
            try:
                data = await response.json()
                message = data.get('message', f"API error: {response.status}")
                raise UNMSAPIError(message)
            except json.JSONDecodeError:
                raise UNMSAPIError(f"API error: {response.status} {response.reason}")
        
        # Parse JSON response
        try:
            if await response.read():
                return await response.json()
            else:
                return None
        except json.JSONDecodeError:
            return await response.text()
    
    @asynccontextmanager
    async def _request_context(self, endpoint: str, method: str, cache_key: Optional[str] = None, 
                             cache_ttl: Optional[int] = None, skip_cache: bool = False) -> Any:
        """
        Context manager for API requests with caching.
        
        Args:
            endpoint (str): API endpoint.
            method (str): HTTP method.
            cache_key (Optional[str], optional): Cache key. Defaults to None.
            cache_ttl (Optional[int], optional): Cache TTL in seconds. Defaults to None.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Yields:
            Dict[str, Any]: Request context.
        """
        context = {
            'url': self._get_endpoint_url(endpoint),
            'method': method.upper(),
            'headers': {},
            'cached': False,
            'data': None,
            'rate_limits': {}
        }
        
        # Add authentication headers
        if self.auth_manager.has_token():
            context['headers'].update(self.auth_manager.get_auth_headers())
        
        # Check cache if applicable
        if (
            method.upper() == 'GET' and 
            not skip_cache and 
            self.cache_manager.is_enabled() and 
            cache_key
        ):
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                context['cached'] = True
                context['data'] = cached_data
                logger.debug(f"Cache hit for {cache_key}")
                yield context
                return
        
        # Execute request
        try:
            yield context
            
            # Store in cache if applicable
            if (
                method.upper() == 'GET' and 
                not skip_cache and 
                self.cache_manager.is_enabled() and 
                cache_key and 
                context.get('data') is not None
            ):
                self.cache_manager.set(cache_key, context['data'], ttl=cache_ttl)
                logger.debug(f"Cached response for {cache_key}")
        
        except Exception:
            # Ensure exceptions are propagated
            raise
    
    async def request(
        self, 
        endpoint: str, 
        method: str = 'GET', 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        expected_status: Optional[List[int]] = None,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
        skip_cache: bool = False
    ) -> Any:
        """
        Make a request to the API.
        
        Args:
            endpoint (str): API endpoint.
            method (str, optional): HTTP method. Defaults to 'GET'.
            params (Optional[Dict[str, Any]], optional): Query parameters. Defaults to None.
            data (Optional[Dict[str, Any]], optional): Form data. Defaults to None.
            json_data (Optional[Dict[str, Any]], optional): JSON data. Defaults to None.
            headers (Optional[Dict[str, Any]], optional): Additional headers. Defaults to None.
            expected_status (Optional[List[int]], optional): Expected status codes. Defaults to None.
            cache_key (Optional[str], optional): Cache key. Defaults to None.
            cache_ttl (Optional[int], optional): Cache TTL in seconds. Defaults to None.
            skip_cache (bool, optional): Whether to skip cache. Defaults to False.
            
        Returns:
            Any: Response data.
        """
        # Generate cache key if not provided
        if cache_key is None and method.upper() == 'GET' and self.cache_manager.is_enabled() and not skip_cache:
            cache_key = generate_cache_key(endpoint, params)
        
        # Use request context
        async with self._request_context(
            endpoint=endpoint,
            method=method,
            cache_key=cache_key,
            cache_ttl=cache_ttl,
            skip_cache=skip_cache
        ) as context:
            # Return cached data if available
            if context['cached']:
                return context['data']
            
            # Get session
            session = await self._get_session()
            
            # Prepare request arguments
            request_kwargs = {
                'method': context['method'],
                'url': context['url'],
                'params': params,
                'data': data,
                'json': json_data,
                'ssl': self.ssl_verify
            }
            
            # Merge headers
            request_headers = context['headers'].copy()
            if headers:
                request_headers.update(headers)
            
            if request_headers:
                request_kwargs['headers'] = request_headers
            
            # Execute request with retry logic
            async def _execute_request():
                async with session.request(**request_kwargs) as response:
                    # Parse rate limit headers
                    context['rate_limits'] = parse_rate_limit_headers(response.headers)
                    
                    # Handle response
                    data = await self._handle_response(response, expected_status)
                    context['data'] = data
                    return data
            
            return await self._with_retry(_execute_request)
    
    # Convenience methods for common HTTP methods
    async def get(self, endpoint: str, **kwargs) -> Any:
        """
        Make a GET request to the API.
        
        Args:
            endpoint (str): API endpoint.
            **kwargs: Additional arguments for request().
            
        Returns:
            Any: Response data.
        """
        return await self.request(endpoint, method='GET', **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Any:
        """
        Make a POST request to the API.
        
        Args:
            endpoint (str): API endpoint.
            **kwargs: Additional arguments for request().
            
        Returns:
            Any: Response data.
        """
        return await self.request(endpoint, method='POST', **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Any:
        """
        Make a PUT request to the API.
        
        Args:
            endpoint (str): API endpoint.
            **kwargs: Additional arguments for request().
            
        Returns:
            Any: Response data.
        """
        return await self.request(endpoint, method='PUT', **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Any:
        """
        Make a DELETE request to the API.
        
        Args:
            endpoint (str): API endpoint.
            **kwargs: Additional arguments for request().
            
        Returns:
            Any: Response data.
        """
        return await self.request(endpoint, method='DELETE', **kwargs)
    
    async def patch(self, endpoint: str, **kwargs) -> Any:
        """
        Make a PATCH request to the API.
        
        Args:
            endpoint (str): API endpoint.
            **kwargs: Additional arguments for request().
            
        Returns:
            Any: Response data.
        """
        return await self.request(endpoint, method='PATCH', **kwargs)
    
    # Authentication methods
    async def login(self, username: str, password: str) -> bool:
        """
        Log in to the UNMS API.
        
        Args:
            username (str): Username.
            password (str): Password.
            
        Returns:
            bool: Whether login was successful.
        """
        session = await self._get_session()
        return await self.auth_manager.login(username, password, session)
    
    async def logout(self) -> bool:
        """
        Log out from the UNMS API.
        
        Returns:
            bool: Whether logout was successful.
        """
        session = await self._get_session()
        return await self.auth_manager.logout(session)
    
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
    
    # Cache methods
    def clear_cache(self) -> None:
        """
        Clear the cache.
        """
        self.cache_manager.clear()
    
    def invalidate_cache(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern (str): Pattern to match.
            
        Returns:
            int: Number of invalidated entries.
        """
        return self.cache_manager.invalidate(pattern)
