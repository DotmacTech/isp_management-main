"""
HATEOAS (Hypermedia as the Engine of Application State) utilities.

This module provides functions to add hypermedia links to API responses,
making the API more self-documenting and discoverable.
"""

from typing import Dict, List, Optional, Any, Union, Type
from pydantic import BaseModel

from backend_core.schemas import Link, HateoasResponse, PaginatedResponse


def add_link(response: Union[HateoasResponse, PaginatedResponse], 
             rel: str, 
             href: str, 
             method: str = "GET", 
             title: Optional[str] = None) -> None:
    """
    Add a HATEOAS link to a response.
    
    Args:
        response: The response object to add the link to
        rel: Relationship of the link to the current resource
        href: URL of the linked resource
        method: HTTP method to use with this link
        title: Human-readable title for the link
    """
    response._links[rel] = Link(
        href=href,
        rel=rel,
        method=method,
        title=title
    )


def generate_collection_links(
    resource_path: str,
    page: int,
    limit: int,
    total: int,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Link]:
    """
    Generate standard HATEOAS links for a collection resource.
    
    Args:
        resource_path: Base path of the resource (e.g., '/api/v1/customers')
        page: Current page number (1-based)
        limit: Number of items per page
        total: Total number of items
        filters: Optional query parameters for filtering
        
    Returns:
        Dict of HATEOAS links
    """
    links = {}
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    
    # Build query string from filters
    query_params = []
    if filters:
        for key, value in filters.items():
            if value is not None:
                query_params.append(f"{key}={value}")
    
    # Add limit to query params
    query_params.append(f"limit={limit}")
    
    # Build base URL
    base_url = f"{resource_path}?"
    filter_string = "&".join(query_params)
    
    # Self link
    self_url = f"{base_url}page={page}&{filter_string}"
    links["self"] = Link(href=self_url, rel="self", method="GET", title="Current page")
    
    # First page link
    first_url = f"{base_url}page=1&{filter_string}"
    links["first"] = Link(href=first_url, rel="first", method="GET", title="First page")
    
    # Last page link
    last_url = f"{base_url}page={total_pages}&{filter_string}"
    links["last"] = Link(href=last_url, rel="last", method="GET", title="Last page")
    
    # Previous page link
    if page > 1:
        prev_url = f"{base_url}page={page-1}&{filter_string}"
        links["prev"] = Link(href=prev_url, rel="prev", method="GET", title="Previous page")
    
    # Next page link
    if page < total_pages:
        next_url = f"{base_url}page={page+1}&{filter_string}"
        links["next"] = Link(href=next_url, rel="next", method="GET", title="Next page")
    
    return links


def add_resource_links(
    response: HateoasResponse,
    resource_path: str,
    resource_id: Union[int, str],
    related_resources: Optional[List[str]] = None
) -> None:
    """
    Add standard HATEOAS links to a resource response.
    
    Args:
        response: The response object to add links to
        resource_path: Base path of the resource (e.g., '/api/v1/customers')
        resource_id: ID of the resource
        related_resources: List of related resources to link to
    """
    # Self link
    add_link(
        response=response,
        rel="self",
        href=f"{resource_path}/{resource_id}",
        method="GET",
        title="Get this resource"
    )
    
    # Collection link
    add_link(
        response=response,
        rel="collection",
        href=resource_path,
        method="GET",
        title="Get all resources"
    )
    
    # Update link
    add_link(
        response=response,
        rel="update",
        href=f"{resource_path}/{resource_id}",
        method="PUT",
        title="Update this resource"
    )
    
    # Delete link
    add_link(
        response=response,
        rel="delete",
        href=f"{resource_path}/{resource_id}",
        method="DELETE",
        title="Delete this resource"
    )
    
    # Add links to related resources
    if related_resources:
        for related in related_resources:
            add_link(
                response=response,
                rel=related,
                href=f"{resource_path}/{resource_id}/{related}",
                method="GET",
                title=f"Get {related} for this resource"
            )
