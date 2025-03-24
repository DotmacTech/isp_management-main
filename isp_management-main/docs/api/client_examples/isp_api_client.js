/**
 * ISP Management Platform API Client
 * 
 * A JavaScript client library for interacting with the ISP Management Platform API.
 * This client takes advantage of HATEOAS links, handles rate limiting, and provides
 * standardized error handling.
 */

class IspApiClient {
  /**
   * Create a new API client instance
   * 
   * @param {string} baseUrl - The base URL of the API (e.g., 'https://api.example.com')
   * @param {string} apiKey - API key for authentication
   */
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.rateLimits = {
      limit: Infinity,
      remaining: Infinity,
      reset: 0
    };
    
    // Cache for discovered links
    this.linkCache = {};
  }

  /**
   * Make an API request with automatic rate limit handling
   * 
   * @param {string} url - The URL to request
   * @param {Object} options - Fetch options
   * @returns {Promise<Object>} - The response data
   */
  async request(url, options = {}) {
    // Add authentication
    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
      ...options.headers
    };

    // Check if we're rate limited
    if (this.rateLimits.remaining <= 0) {
      const now = Math.floor(Date.now() / 1000);
      const waitTime = Math.max(0, this.rateLimits.reset - now);
      
      if (waitTime > 0) {
        console.warn(`Rate limit reached. Waiting ${waitTime} seconds before retrying.`);
        await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
      }
    }

    // Make the request
    const response = await fetch(url.startsWith('http') ? url : `${this.baseUrl}${url}`, {
      ...options,
      headers
    });

    // Update rate limit information
    this.updateRateLimits(response);

    // Parse the response
    const data = await response.json();

    // Handle error responses
    if (response.status >= 400) {
      throw this.createErrorFromResponse(data, response.status);
    }

    // Cache any links in the response
    if (data._links) {
      this.cacheLinks(url, data._links);
    }

    return data;
  }

  /**
   * Update rate limit information from response headers
   * 
   * @param {Response} response - Fetch Response object
   */
  updateRateLimits(response) {
    const limit = response.headers.get('X-RateLimit-Limit');
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const reset = response.headers.get('X-RateLimit-Reset');

    if (limit) this.rateLimits.limit = parseInt(limit);
    if (remaining) this.rateLimits.remaining = parseInt(remaining);
    if (reset) this.rateLimits.reset = parseInt(reset);
  }

  /**
   * Create a standardized error object from an API error response
   * 
   * @param {Object} data - Error response data
   * @param {number} status - HTTP status code
   * @returns {Error} - Enhanced error object
   */
  createErrorFromResponse(data, status) {
    const error = new Error(data.message || 'API request failed');
    error.status = status;
    error.code = data.code || status;
    error.details = data.details || {};
    
    // Add helper for validation errors
    if (error.details.field_errors) {
      error.getFieldError = (fieldName) => {
        const fieldError = error.details.field_errors.find(e => e.field === fieldName);
        return fieldError ? fieldError.message : null;
      };
    }
    
    return error;
  }

  /**
   * Cache links from a response for later use
   * 
   * @param {string} url - The URL that was requested
   * @param {Object} links - The _links object from the response
   */
  cacheLinks(url, links) {
    this.linkCache[url] = links;
  }

  /**
   * Follow a link from a previous response
   * 
   * @param {Object} resource - Resource containing _links
   * @param {string} rel - The link relation to follow
   * @param {Object} options - Additional fetch options
   * @returns {Promise<Object>} - The response data
   */
  async followLink(resource, rel, options = {}) {
    if (!resource._links || !resource._links[rel]) {
      throw new Error(`Link relation '${rel}' not found in resource`);
    }

    const link = resource._links[rel];
    return this.request(link.href, {
      method: link.method || 'GET',
      ...options
    });
  }

  /**
   * Get a list of customers with optional filtering
   * 
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} - Paginated customer list with HATEOAS links
   */
  async getCustomers(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/customers${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  /**
   * Get a customer by ID
   * 
   * @param {string|number} id - Customer ID
   * @returns {Promise<Object>} - Customer data with HATEOAS links
   */
  async getCustomer(id) {
    return this.request(`/api/v1/customers/${id}`);
  }

  /**
   * Create a new customer
   * 
   * @param {Object} customerData - Customer data
   * @returns {Promise<Object>} - Created customer with HATEOAS links
   */
  async createCustomer(customerData) {
    return this.request('/api/v1/customers', {
      method: 'POST',
      body: JSON.stringify(customerData)
    });
  }

  /**
   * Update a customer
   * 
   * @param {string|number} id - Customer ID
   * @param {Object} customerData - Updated customer data
   * @returns {Promise<Object>} - Updated customer with HATEOAS links
   */
  async updateCustomer(id, customerData) {
    return this.request(`/api/v1/customers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(customerData)
    });
  }

  /**
   * Delete a customer
   * 
   * @param {string|number} id - Customer ID
   * @returns {Promise<Object>} - Response data
   */
  async deleteCustomer(id) {
    return this.request(`/api/v1/customers/${id}`, {
      method: 'DELETE'
    });
  }

  /**
   * Get customer addresses
   * 
   * @param {Object} customer - Customer resource with _links
   * @returns {Promise<Object>} - Customer addresses with HATEOAS links
   */
  async getCustomerAddresses(customer) {
    return this.followLink(customer, 'addresses');
  }

  /**
   * Get customer contacts
   * 
   * @param {Object} customer - Customer resource with _links
   * @returns {Promise<Object>} - Customer contacts with HATEOAS links
   */
  async getCustomerContacts(customer) {
    return this.followLink(customer, 'contacts');
  }

  /**
   * Get customer documents
   * 
   * @param {Object} customer - Customer resource with _links
   * @returns {Promise<Object>} - Customer documents with HATEOAS links
   */
  async getCustomerDocuments(customer) {
    return this.followLink(customer, 'documents');
  }

  /**
   * Get customer subscription
   * 
   * @param {Object} customer - Customer resource with _links
   * @returns {Promise<Object>} - Customer subscription with HATEOAS links
   */
  async getCustomerSubscription(customer) {
    return this.followLink(customer, 'subscription');
  }

  /**
   * Get customer billing information
   * 
   * @param {Object} customer - Customer resource with _links
   * @returns {Promise<Object>} - Customer billing with HATEOAS links
   */
  async getCustomerBilling(customer) {
    return this.followLink(customer, 'billing');
  }

  /**
   * Navigate to the next page of a collection
   * 
   * @param {Object} collection - Collection resource with _links
   * @returns {Promise<Object>} - Next page of the collection
   */
  async getNextPage(collection) {
    return this.followLink(collection, 'next');
  }

  /**
   * Navigate to the previous page of a collection
   * 
   * @param {Object} collection - Collection resource with _links
   * @returns {Promise<Object>} - Previous page of the collection
   */
  async getPreviousPage(collection) {
    return this.followLink(collection, 'prev');
  }

  /**
   * Navigate to the first page of a collection
   * 
   * @param {Object} collection - Collection resource with _links
   * @returns {Promise<Object>} - First page of the collection
   */
  async getFirstPage(collection) {
    return this.followLink(collection, 'first');
  }

  /**
   * Navigate to the last page of a collection
   * 
   * @param {Object} collection - Collection resource with _links
   * @returns {Promise<Object>} - Last page of the collection
   */
  async getLastPage(collection) {
    return this.followLink(collection, 'last');
  }

  /**
   * Get alert configurations
   * 
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} - Paginated alert configurations with HATEOAS links
   */
  async getAlertConfigurations(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/monitoring/alert-configurations${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  /**
   * Get alert history
   * 
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} - Paginated alert history with HATEOAS links
   */
  async getAlertHistory(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/monitoring/alert-history${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }
}

// Example usage
async function exampleUsage() {
  try {
    // Initialize the client
    const client = new IspApiClient('https://api.example.com', 'your-api-key');
    
    // Get customers (first page)
    const customers = await client.getCustomers({ limit: 10 });
    console.log(`Found ${customers.total} customers`);
    
    // Navigate to the next page using HATEOAS links
    if (customers._links.next) {
      const nextPage = await client.getNextPage(customers);
      console.log(`Showing customers ${nextPage.skip + 1} to ${nextPage.skip + nextPage.items.length}`);
    }
    
    // Get a specific customer
    const customer = await client.getCustomer(123);
    console.log(`Customer: ${customer.name}`);
    
    // Get customer addresses using HATEOAS links
    const addresses = await client.getCustomerAddresses(customer);
    console.log(`Customer has ${addresses.items.length} addresses`);
    
    // Create a new customer
    const newCustomer = await client.createCustomer({
      name: 'New Customer',
      email: 'new@example.com'
    });
    console.log(`Created customer with ID: ${newCustomer.id}`);
    
  } catch (error) {
    console.error('API Error:', error.message);
    
    // Handle validation errors
    if (error.details && error.details.field_errors) {
      error.details.field_errors.forEach(fieldError => {
        console.error(`${fieldError.field}: ${fieldError.message}`);
      });
    }
  }
}

// Export the client class
if (typeof module !== 'undefined') {
  module.exports = { IspApiClient };
}
