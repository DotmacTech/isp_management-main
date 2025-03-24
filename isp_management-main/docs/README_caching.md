# ISP Management Platform - Caching System

## Overview

This document provides a comprehensive guide to the Redis-based caching system implemented in the ISP Management Platform. The caching system is designed to improve performance by reducing database load for frequently accessed data in the billing module.

## Getting Started

### Prerequisites

- Redis server (version 6.0 or higher recommended)
- Python 3.8+
- ISP Management Platform codebase

### Configuration

The caching system is configured through environment variables:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password  # Leave empty if no password
```

These settings can be found in `backend_core/config.py`.

## Architecture

The caching implementation follows a layered approach:

1. **Core Cache Layer**: Basic Redis operations (get, set, delete)
2. **Domain-Specific Cache Layer**: Functions for specific data types (tax rates, discounts, etc.)
3. **Service Layer Integration**: Billing service methods that use the cache

### Cache Types and TTL

| Data Type | Cache Key Pattern | TTL | Invalidation Trigger |
|-----------|-------------------|-----|----------------------|
| Tax Rates | `tax_rate:{country}:{region}` | 24 hours | When tax rates are updated |
| Active Discounts | `active_discounts` | 1 hour | When discounts are applied or updated |
| Invoice Details | `invoice:{invoice_id}` | 5 minutes | When invoice is modified (payments, discounts, taxes) |
| User Credit Notes | `user_credit_notes:{user_id}` | 10 minutes | When credit notes are created or applied |

## Using the Cache

### In Service Methods

The caching system is integrated into the billing service methods. Here's an example of how to use it:

```python
def get_invoice_details(self, invoice_id: int):
    """Get detailed invoice information."""
    # Try to get from cache first
    cached_details = get_cached_invoice_details(invoice_id)
    if cached_details:
        return cached_details
    
    # If not in cache, get from database
    invoice = self.get_invoice(invoice_id)
    if not invoice:
        return None
    
    # Process invoice details...
    details = {...}  # Process invoice details
    
    # Cache the result
    cache_invoice_details(invoice_id, details)
    
    return details
```

### Cache Invalidation

When modifying data that's cached, make sure to invalidate the cache:

```python
def process_payment(self, payment_data):
    """Process a payment for an invoice."""
    # Process payment...
    
    # Invalidate invoice cache
    invalidate_invoice_cache(payment_data.invoice_id)
```

## Utility Scripts

### Cache Performance Monitoring

The `scripts/monitor_cache_performance.py` script helps monitor cache performance:

```bash
python scripts/monitor_cache_performance.py --iterations 100
```

This will generate a report showing:
- Cache hit/miss rates
- Average response times (cached vs. database)
- Performance improvement percentages

### Cache Management

The `scripts/cache_management.py` utility provides tools for managing the cache:

```bash
# View cache statistics
python scripts/cache_management.py stats

# Clear specific cache types
python scripts/cache_management.py clear --type invoices

# Clear all cache
python scripts/cache_management.py clear --type all

# Warm up cache with frequently accessed data
python scripts/cache_management.py warmup
```

## Model Serialization

Database models include `to_dict()` methods for proper serialization when caching:

```python
# Example from Invoice model
def to_dict(self):
    """Convert invoice to dictionary for caching."""
    return {
        "id": self.id,
        "user_id": self.user_id,
        "amount": str(self.amount),
        "status": self.status,
        "due_date": self.due_date.isoformat() if self.due_date else None,
        # ... other fields
    }
```

## Best Practices

1. **Always invalidate cache** when modifying data that might be cached
2. **Use appropriate TTL values** based on data volatility
3. **Handle cache misses gracefully** by falling back to database queries
4. **Monitor cache performance** to identify optimization opportunities
5. **Warm up cache** after deployments or cache clears

## Troubleshooting

### Common Issues

1. **Cache inconsistency**: If data appears outdated, check that invalidation is properly implemented
2. **Redis connection failures**: Verify Redis server is running and connection settings are correct
3. **High memory usage**: Consider reducing TTL values or being more selective about what's cached

### Debugging

Enable debug logging to see cache operations:

```python
import logging
logging.getLogger('isp_management.backend_core.cache').setLevel(logging.DEBUG)
```

## Performance Considerations

- **Memory usage**: Monitor Redis memory usage and configure maxmemory settings
- **Network latency**: Consider placing Redis close to your application servers
- **Serialization overhead**: Be mindful of the cost of serializing/deserializing complex objects

## Future Enhancements

Planned improvements to the caching system:

1. Distributed cache invalidation for multi-instance deployments
2. Circuit breaker pattern for Redis connection failures
3. Cache analytics dashboard
4. Automated cache warming based on usage patterns

## Contributing

When extending the caching system:

1. Follow the existing patterns for cache key naming
2. Add appropriate TTL values for new cache types
3. Implement proper invalidation logic
4. Update this documentation with new cache types

## References

- [Redis Documentation](https://redis.io/documentation)
- [FastAPI Caching Best Practices](https://fastapi.tiangolo.com/)
- [SQLAlchemy and Caching](https://docs.sqlalchemy.org/en/14/orm/extensions/caching.html)
