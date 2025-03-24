"""
ISP Management Platform API Client

A Python client library for interacting with the ISP Management Platform API.
This client takes advantage of HATEOAS links, handles rate limiting, and provides
standardized error handling.
"""

import time
import json
import urllib.parse
from typing import Dict, List, Any, Optional, Union
import requests


class ApiError(Exception):
    """Custom exception for API errors with detailed information."""
    
    def __init__(self, message: str, status: int, code: int = None, details: Dict = None):
        self.message = message
        self.status = status
        self.code = code or status
        self.details = details or {}
        super().__init__(self.message)
    
    def get_field_error(self, field_name: str) -> Optional[str]:
        """Get error message for a specific field."""
        if not self.details or 'field_errors' not in self.details:
            return None
        
        for field_error in self.details['field_errors']:
            if field_error['field'] == field_name:
                return field_error['message']
        
        return None


class IspApiClient:
    """
    Client for the ISP Management Platform API.
    
    This client handles authentication, rate limiting, and provides methods
    for interacting with the API resources. It also takes advantage of HATEOAS
    links for navigation.
    """
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the API client.
        
        Args:
            base_url: The base URL of the API (e.g., 'https://api.example.com')
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.rate_limits = {
            'limit': float('inf'),
            'remaining': float('inf'),
            'reset': 0
        }
        
        # Cache for discovered links
        self.link_cache = {}
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def request(self, url: str, method: str = 'GET', data: Dict = None, 
                params: Dict = None, headers: Dict = None) -> Dict:
        """
        Make an API request with automatic rate limit handling.
        
        Args:
            url: The URL to request
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            The response data
            
        Raises:
            ApiError: If the API returns an error response
        """
        # Check if we're rate limited
        if self.rate_limits['remaining'] <= 0:
            now = int(time.time())
            wait_time = max(0, self.rate_limits['reset'] - now)
            
            if wait_time > 0:
                print(f"Rate limit reached. Waiting {wait_time} seconds before retrying.")
                time.sleep(wait_time)
        
        # Prepare the request
        full_url = url if url.startswith('http') else f"{self.base_url}{url}"
        request_headers = headers or {}
        
        # Make the request
        response = self.session.request(
            method=method,
            url=full_url,
            json=data if data else None,
            params=params,
            headers=request_headers
        )
        
        # Update rate limit information
        self._update_rate_limits(response)
        
        # Parse the response
        try:
            response_data = response.json()
        except ValueError:
            response_data = {'message': 'Invalid JSON response'}
        
        # Handle error responses
        if response.status_code >= 400:
            raise self._create_error_from_response(response_data, response.status_code)
        
        # Cache any links in the response
        if '_links' in response_data:
            self._cache_links(url, response_data['_links'])
        
        return response_data
    
    def _update_rate_limits(self, response: requests.Response) -> None:
        """
        Update rate limit information from response headers.
        
        Args:
            response: Requests Response object
        """
        limit = response.headers.get('X-RateLimit-Limit')
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset = response.headers.get('X-RateLimit-Reset')
        
        if limit:
            self.rate_limits['limit'] = int(limit)
        if remaining:
            self.rate_limits['remaining'] = int(remaining)
        if reset:
            self.rate_limits['reset'] = int(reset)
    
    def _create_error_from_response(self, data: Dict, status: int) -> ApiError:
        """
        Create a standardized error object from an API error response.
        
        Args:
            data: Error response data
            status: HTTP status code
            
        Returns:
            Enhanced ApiError object
        """
        return ApiError(
            message=data.get('message', 'API request failed'),
            status=status,
            code=data.get('code', status),
            details=data.get('details', {})
        )
    
    def _cache_links(self, url: str, links: Dict) -> None:
        """
        Cache links from a response for later use.
        
        Args:
            url: The URL that was requested
            links: The _links object from the response
        """
        self.link_cache[url] = links
    
    def follow_link(self, resource: Dict, rel: str, method: str = None, 
                   data: Dict = None, params: Dict = None) -> Dict:
        """
        Follow a link from a previous response.
        
        Args:
            resource: Resource containing _links
            rel: The link relation to follow
            method: HTTP method override
            data: Request body data
            params: Query parameters
            
        Returns:
            The response data
            
        Raises:
            ValueError: If the link relation is not found
        """
        if '_links' not in resource or rel not in resource['_links']:
            raise ValueError(f"Link relation '{rel}' not found in resource")
        
        link = resource['_links'][rel]
        return self.request(
            url=link['href'],
            method=method or link.get('method', 'GET'),
            data=data,
            params=params
        )
    
    # Customer endpoints
    
    def get_customers(self, **params) -> Dict:
        """
        Get a list of customers with optional filtering.
        
        Args:
            **params: Query parameters (skip, limit, customer_type, etc.)
            
        Returns:
            Paginated customer list with HATEOAS links
        """
        url = '/api/v1/customers'
        return self.request(url, params=params)
    
    def get_customer(self, customer_id: Union[str, int]) -> Dict:
        """
        Get a customer by ID.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer data with HATEOAS links
        """
        url = f'/api/v1/customers/{customer_id}'
        return self.request(url)
    
    def create_customer(self, customer_data: Dict) -> Dict:
        """
        Create a new customer.
        
        Args:
            customer_data: Customer data
            
        Returns:
            Created customer with HATEOAS links
        """
        url = '/api/v1/customers'
        return self.request(url, method='POST', data=customer_data)
    
    def update_customer(self, customer_id: Union[str, int], customer_data: Dict) -> Dict:
        """
        Update a customer.
        
        Args:
            customer_id: Customer ID
            customer_data: Updated customer data
            
        Returns:
            Updated customer with HATEOAS links
        """
        url = f'/api/v1/customers/{customer_id}'
        return self.request(url, method='PUT', data=customer_data)
    
    def delete_customer(self, customer_id: Union[str, int]) -> Dict:
        """
        Delete a customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Response data
        """
        url = f'/api/v1/customers/{customer_id}'
        return self.request(url, method='DELETE')
    
    # Customer related resources
    
    def get_customer_addresses(self, customer: Dict) -> Dict:
        """
        Get customer addresses using HATEOAS link.
        
        Args:
            customer: Customer resource with _links
            
        Returns:
            Customer addresses with HATEOAS links
        """
        return self.follow_link(customer, 'addresses')
    
    def get_customer_contacts(self, customer: Dict) -> Dict:
        """
        Get customer contacts using HATEOAS link.
        
        Args:
            customer: Customer resource with _links
            
        Returns:
            Customer contacts with HATEOAS links
        """
        return self.follow_link(customer, 'contacts')
    
    def get_customer_documents(self, customer: Dict) -> Dict:
        """
        Get customer documents using HATEOAS link.
        
        Args:
            customer: Customer resource with _links
            
        Returns:
            Customer documents with HATEOAS links
        """
        return self.follow_link(customer, 'documents')
    
    def get_customer_subscription(self, customer: Dict) -> Dict:
        """
        Get customer subscription using HATEOAS link.
        
        Args:
            customer: Customer resource with _links
            
        Returns:
            Customer subscription with HATEOAS links
        """
        return self.follow_link(customer, 'subscription')
    
    def get_customer_billing(self, customer: Dict) -> Dict:
        """
        Get customer billing information using HATEOAS link.
        
        Args:
            customer: Customer resource with _links
            
        Returns:
            Customer billing with HATEOAS links
        """
        return self.follow_link(customer, 'billing')
    
    # Pagination helpers
    
    def get_next_page(self, collection: Dict) -> Dict:
        """
        Navigate to the next page of a collection.
        
        Args:
            collection: Collection resource with _links
            
        Returns:
            Next page of the collection
        """
        return self.follow_link(collection, 'next')
    
    def get_previous_page(self, collection: Dict) -> Dict:
        """
        Navigate to the previous page of a collection.
        
        Args:
            collection: Collection resource with _links
            
        Returns:
            Previous page of the collection
        """
        return self.follow_link(collection, 'prev')
    
    def get_first_page(self, collection: Dict) -> Dict:
        """
        Navigate to the first page of a collection.
        
        Args:
            collection: Collection resource with _links
            
        Returns:
            First page of the collection
        """
        return self.follow_link(collection, 'first')
    
    def get_last_page(self, collection: Dict) -> Dict:
        """
        Navigate to the last page of a collection.
        
        Args:
            collection: Collection resource with _links
            
        Returns:
            Last page of the collection
        """
        return self.follow_link(collection, 'last')
    
    # Monitoring endpoints
    
    def get_alert_configurations(self, **params) -> Dict:
        """
        Get alert configurations with optional filtering.
        
        Args:
            **params: Query parameters (skip, limit, service_name, is_active)
            
        Returns:
            Paginated alert configurations with HATEOAS links
        """
        url = '/api/v1/monitoring/alert-configurations'
        return self.request(url, params=params)
    
    def get_alert_history(self, **params) -> Dict:
        """
        Get alert history with optional filtering.
        
        Args:
            **params: Query parameters (skip, limit, service_names, severities, etc.)
            
        Returns:
            Paginated alert history with HATEOAS links
        """
        url = '/api/v1/monitoring/alert-history'
        return self.request(url, params=params)


# Example usage
def example_usage():
    """Example of using the API client."""
    try:
        # Initialize the client
        client = IspApiClient('https://api.example.com', 'your-api-key')
        
        # Get customers (first page)
        customers = client.get_customers(limit=10)
        print(f"Found {customers['total']} customers")
        
        # Navigate to the next page using HATEOAS links
        if 'next' in customers.get('_links', {}):
            next_page = client.get_next_page(customers)
            print(f"Showing customers {next_page['skip'] + 1} to {next_page['skip'] + len(next_page['items'])}")
        
        # Get a specific customer
        customer = client.get_customer(123)
        print(f"Customer: {customer['name']}")
        
        # Get customer addresses using HATEOAS links
        addresses = client.get_customer_addresses(customer)
        print(f"Customer has {len(addresses['items'])} addresses")
        
        # Create a new customer
        new_customer = client.create_customer({
            'name': 'New Customer',
            'email': 'new@example.com'
        })
        print(f"Created customer with ID: {new_customer['id']}")
        
    except ApiError as e:
        print(f"API Error ({e.status}): {e.message}")
        
        # Handle validation errors
        if e.details and 'field_errors' in e.details:
            for field_error in e.details['field_errors']:
                print(f"{field_error['field']}: {field_error['message']}")


if __name__ == '__main__':
    example_usage()
