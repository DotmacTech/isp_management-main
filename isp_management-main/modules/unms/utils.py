"""
Utility functions for the UNMS API client.
"""
import hashlib
import json
import logging
from typing import Optional, Dict, List, Any, Union
from urllib.parse import urljoin

logger = logging.getLogger('unms_api')


def generate_cache_key(endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a cache key for an API request.
    
    Args:
        endpoint (str): API endpoint.
        params (Optional[Dict[str, Any]], optional): Query parameters. Defaults to None.
        
    Returns:
        str: Cache key.
    """
    key = endpoint
    
    if params:
        # Sort parameters to ensure consistent keys
        sorted_params = sorted(params.items())
        param_str = '&'.join(f"{k}={v}" for k, v in sorted_params)
        key = f"{key}?{param_str}"
    
    # Hash the key to ensure it's a valid cache key
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def validate_params(params: Dict[str, Any], required: List[str] = None, 
                   optional: List[str] = None) -> None:
    """
    Validate API request parameters.
    
    Args:
        params (Dict[str, Any]): Parameters to validate.
        required (List[str], optional): Required parameters. Defaults to None.
        optional (List[str], optional): Optional parameters. Defaults to None.
        
    Raises:
        ValueError: If a required parameter is missing or an unknown parameter is provided.
    """
    required = required or []
    optional = optional or []
    
    # Check for missing required parameters
    missing = [p for p in required if p not in params]
    if missing:
        raise ValueError(f"Missing required parameters: {', '.join(missing)}")
    
    # Check for unknown parameters
    allowed = set(required + optional)
    unknown = [p for p in params if p not in allowed]
    if unknown:
        logger.warning(f"Unknown parameters: {', '.join(unknown)}")


def add_resource_links(data: Dict[str, Any], resource_type: str, resource_id: str, 
                      base_url: str, api_version: str) -> Dict[str, Any]:
    """
    Add HATEOAS links to a resource response.
    
    Args:
        data (Dict[str, Any]): Response data.
        resource_type (str): Resource type (e.g., 'devices', 'sites').
        resource_id (str): Resource ID.
        base_url (str): Base URL of the API.
        api_version (str): API version.
        
    Returns:
        Dict[str, Any]: Response data with HATEOAS links.
    """
    if '_links' not in data:
        data['_links'] = {}
    
    # Add self link
    data['_links']['self'] = {
        'href': f"{base_url}/v{api_version}/{resource_type}/{resource_id}"
    }
    
    # Add collection link
    data['_links']['collection'] = {
        'href': f"{base_url}/v{api_version}/{resource_type}"
    }
    
    return data


def add_collection_links(data: Dict[str, Any], resource_type: str, base_url: str, 
                        api_version: str, page: int = 1, limit: int = 100, 
                        total: Optional[int] = None) -> Dict[str, Any]:
    """
    Add HATEOAS links to a collection response.
    
    Args:
        data (Dict[str, Any]): Response data.
        resource_type (str): Resource type (e.g., 'devices', 'sites').
        base_url (str): Base URL of the API.
        api_version (str): API version.
        page (int, optional): Current page. Defaults to 1.
        limit (int, optional): Items per page. Defaults to 100.
        total (Optional[int], optional): Total number of items. Defaults to None.
        
    Returns:
        Dict[str, Any]: Response data with HATEOAS links.
    """
    if '_links' not in data:
        data['_links'] = {}
    
    # Add self link
    data['_links']['self'] = {
        'href': f"{base_url}/v{api_version}/{resource_type}?page={page}&limit={limit}"
    }
    
    # Add pagination links if total is provided
    if total is not None:
        total_pages = (total + limit - 1) // limit
        
        # Add first page link
        data['_links']['first'] = {
            'href': f"{base_url}/v{api_version}/{resource_type}?page=1&limit={limit}"
        }
        
        # Add previous page link if not on first page
        if page > 1:
            data['_links']['prev'] = {
                'href': f"{base_url}/v{api_version}/{resource_type}?page={page-1}&limit={limit}"
            }
        
        # Add next page link if not on last page
        if page < total_pages:
            data['_links']['next'] = {
                'href': f"{base_url}/v{api_version}/{resource_type}?page={page+1}&limit={limit}"
            }
        
        # Add last page link
        data['_links']['last'] = {
            'href': f"{base_url}/v{api_version}/{resource_type}?page={total_pages}&limit={limit}"
        }
    
    return data


def format_error_response(message: str, status_code: int, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format a standardized error response.
    
    Args:
        message (str): Error message.
        status_code (int): HTTP status code.
        details (Optional[Dict[str, Any]], optional): Error details. Defaults to None.
        
    Returns:
        Dict[str, Any]: Formatted error response.
    """
    response = {
        'error': {
            'message': message,
            'status_code': status_code
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return response


def parse_rate_limit_headers(headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Parse rate limit headers from a response.
    
    Args:
        headers (Dict[str, str]): Response headers.
        
    Returns:
        Dict[str, Any]: Rate limit information.
    """
    rate_limits = {}
    
    # Extract rate limit headers
    limit = headers.get('X-RateLimit-Limit')
    remaining = headers.get('X-RateLimit-Remaining')
    reset = headers.get('X-RateLimit-Reset')
    
    if limit:
        try:
            rate_limits['limit'] = int(limit)
        except ValueError:
            pass
    
    if remaining:
        try:
            rate_limits['remaining'] = int(remaining)
        except ValueError:
            pass
    
    if reset:
        try:
            rate_limits['reset'] = int(reset)
        except ValueError:
            pass
    
    return rate_limits


def extract_link(data: Dict[str, Any], rel: str) -> Optional[str]:
    """
    Extract a link from a HATEOAS _links object.
    
    Args:
        data (Dict[str, Any]): Response data containing _links.
        rel (str): Link relation to extract.
        
    Returns:
        Optional[str]: URL of the link, or None if not found.
    """
    if not data or '_links' not in data:
        return None
    
    links = data['_links']
    if rel not in links:
        return None
    
    link = links[rel]
    if isinstance(link, dict) and 'href' in link:
        return link['href']
    
    return None


def follow_link(client, data: Dict[str, Any], rel: str) -> Optional[Dict[str, Any]]:
    """
    Follow a link from a HATEOAS _links object.
    
    Args:
        client: UNMS API client instance.
        data (Dict[str, Any]): Response data containing _links.
        rel (str): Link relation to follow.
        
    Returns:
        Optional[Dict[str, Any]]: Response data from following the link, or None if not found.
    """
    url = extract_link(data, rel)
    if not url:
        return None
    
    # If the URL is absolute, we need to extract just the endpoint part
    base_url = client.base_url
    if url.startswith(base_url):
        endpoint = url[len(base_url):]
        # Remove the API version prefix if present
        if endpoint.startswith(f"/{client.api_version}"):
            endpoint = endpoint[len(f"/{client.api_version}"):]
    else:
        endpoint = url
    
    # Clean up the endpoint
    endpoint = endpoint.lstrip('/')
    
    # Make the request to the endpoint
    return client.get(endpoint)


def get_resource_links(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Get all resource links from a HATEOAS _links object.
    
    Args:
        data (Dict[str, Any]): Response data containing _links.
        
    Returns:
        Dict[str, str]: Dictionary of link relations to URLs.
    """
    if not data or '_links' not in data:
        return {}
    
    links = {}
    for rel, link_obj in data['_links'].items():
        if isinstance(link_obj, dict) and 'href' in link_obj:
            links[rel] = link_obj['href']
    
    return links


def get_collection_links(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Get all collection links from a HATEOAS _links object.
    
    Args:
        data (Dict[str, Any]): Response data containing _links.
        
    Returns:
        Dict[str, str]: Dictionary of link relations to URLs, focusing on pagination links.
    """
    links = get_resource_links(data)
    
    # Filter to include only pagination-related links
    pagination_rels = ['self', 'first', 'prev', 'next', 'last']
    return {rel: url for rel, url in links.items() if rel in pagination_rels}
