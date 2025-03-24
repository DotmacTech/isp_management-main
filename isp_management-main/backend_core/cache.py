"""
Redis cache implementation for the ISP Management Platform.
This module provides functions for caching frequently accessed data.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal

import redis
from redis.exceptions import RedisError

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Redis connection
redis_client = None
try:
    # Check if Redis configuration is available
    redis_host = getattr(settings, "REDIS_HOST", "localhost")
    redis_port = getattr(settings, "REDIS_PORT", 6379)
    redis_db = getattr(settings, "REDIS_DB", 0)
    redis_password = getattr(settings, "REDIS_PASSWORD", None)
    
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True
    )
    redis_client.ping()  # Test connection
    logger.info("Successfully connected to Redis")
except (RedisError, AttributeError) as e:
    logger.warning(f"Redis connection not available: {e}")
    redis_client = None


def get_redis() -> Optional[redis.Redis]:
    """
    Get the Redis client instance.
    
    Returns:
        Optional[redis.Redis]: Redis client instance or None if not available
    """
    return redis_client

# Cache expiration times (in seconds)
CACHE_EXPIRY = {
    "tax_rates": 3600 * 24,  # 24 hours
    "active_discounts": 3600,  # 1 hour
    "invoice_details": 300,  # 5 minutes
    "user_credit_notes": 600,  # 10 minutes
    "user_invoices": 300,  # 5 minutes
    "payment_history": 600,  # 10 minutes
    "billing_statistics": 1800,  # 30 minutes
    "user_payment_methods": 1800,  # 30 minutes
}

# Cache metrics keys
CACHE_METRICS = {
    "hits": "cache:metrics:hits",
    "misses": "cache:metrics:misses",
    "response_times": "cache:metrics:response_times",
}

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def serialize(data: Any) -> str:
    """Serialize data to JSON string with support for Decimal."""
    return json.dumps(data, cls=DecimalEncoder)

def deserialize(data_str: str) -> Any:
    """Deserialize JSON string to Python object."""
    if not data_str:
        return None
    try:
        return json.loads(data_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to deserialize data: {e}")
        return None

def cache_set(key: str, data: Any, expiry: Optional[int] = None) -> bool:
    """
    Set data in cache with optional expiry time.
    
    Args:
        key: Cache key
        data: Data to cache
        expiry: Expiry time in seconds (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if redis_client is None:
        logger.warning("Redis client not available, skipping cache_set")
        return False
    
    try:
        serialized_data = serialize(data)
        if expiry:
            return redis_client.setex(key, expiry, serialized_data)
        else:
            return redis_client.set(key, serialized_data)
    except (RedisError, TypeError) as e:
        logger.error(f"Failed to set cache for key {key}: {e}")
        return False

def cache_get(key: str) -> Any:
    """
    Get data from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Any: Cached data or None if not found
    """
    if redis_client is None:
        logger.warning("Redis client not available, skipping cache_get")
        return None
    
    start_time = time.time()
    try:
        data = redis_client.get(key)
        response_time = time.time() - start_time
        
        # Record metrics
        if data:
            redis_client.incr(CACHE_METRICS["hits"])
            redis_client.lpush(CACHE_METRICS["response_times"], response_time)
            redis_client.ltrim(CACHE_METRICS["response_times"], 0, 999)  # Keep last 1000 response times
            return deserialize(data)
        else:
            redis_client.incr(CACHE_METRICS["misses"])
            return None
    except RedisError as e:
        logger.error(f"Failed to get cache for key {key}: {e}")
        return None

def cache_delete(key: str) -> bool:
    """
    Delete data from cache.
    
    Args:
        key: Cache key
        
    Returns:
        bool: True if successful, False otherwise
    """
    if redis_client is None:
        logger.warning("Redis client not available, skipping cache_delete")
        return False
    
    try:
        return bool(redis_client.delete(key))
    except RedisError as e:
        logger.error(f"Failed to delete cache for key {key}: {e}")
        return False

def cache_clear_pattern(pattern: str) -> bool:
    """
    Clear all cache keys matching a pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "tax_rate:*")
        
    Returns:
        bool: True if successful, False otherwise
    """
    if redis_client is None:
        logger.warning("Redis client not available, skipping cache_clear_pattern")
        return False
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            return bool(redis_client.delete(*keys))
        return True  # No keys to delete is still a success
    except RedisError as e:
        logger.error(f"Failed to clear cache for pattern {pattern}: {e}")
        return False

# Cache monitoring functions
def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics including hit rate, miss rate, and response times.
    
    Returns:
        Dict: Cache statistics
    """
    if redis_client is None:
        logger.warning("Redis client not available, skipping get_cache_stats")
        return {"error": "Redis client not available"}
    
    try:
        hits = int(redis_client.get(CACHE_METRICS["hits"]) or 0)
        misses = int(redis_client.get(CACHE_METRICS["misses"]) or 0)
        total = hits + misses
        
        # Calculate hit rate and miss rate
        hit_rate = (hits / total) * 100 if total > 0 else 0
        miss_rate = (misses / total) * 100 if total > 0 else 0
        
        # Get response times
        response_times = [float(t) for t in redis_client.lrange(CACHE_METRICS["response_times"], 0, -1)]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Get memory usage
        memory_info = redis_client.info("memory")
        
        return {
            "hits": hits,
            "misses": misses,
            "total_requests": total,
            "hit_rate": hit_rate,
            "miss_rate": miss_rate,
            "avg_response_time": avg_response_time,
            "memory_usage": memory_info.get("used_memory_human", "N/A"),
            "peak_memory": memory_info.get("used_memory_peak_human", "N/A"),
        }
    except RedisError as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {"error": str(e)}

def reset_cache_stats() -> bool:
    """
    Reset cache statistics.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if redis_client is None:
        logger.warning("Redis client not available, skipping reset_cache_stats")
        return False
    
    try:
        redis_client.set(CACHE_METRICS["hits"], 0)
        redis_client.set(CACHE_METRICS["misses"], 0)
        redis_client.delete(CACHE_METRICS["response_times"])
        return True
    except RedisError as e:
        logger.error(f"Failed to reset cache stats: {e}")
        return False

# Specific caching functions for billing module

def cache_tax_rate(country: str, region: Optional[str], tax_rate: Dict) -> bool:
    """Cache tax rate for a specific country/region."""
    key = f"tax_rate:{country}:{region or 'default'}"
    return cache_set(key, tax_rate, CACHE_EXPIRY["tax_rates"])

def get_cached_tax_rate(country: str, region: Optional[str]) -> Optional[Dict]:
    """Get cached tax rate for a specific country/region."""
    key = f"tax_rate:{country}:{region or 'default'}"
    return cache_get(key)

def invalidate_tax_rate_cache(country: str, region: Optional[str] = None):
    """Invalidate tax rate cache for a specific country/region."""
    if region:
        key = f"tax_rate:{country.lower()}:{region.lower()}"
    else:
        key = f"tax_rate:{country.lower()}"
    return cache_delete(key)

def cache_active_discounts(discounts: List[Dict]) -> bool:
    """Cache active discounts."""
    return cache_set("active_discounts", discounts, CACHE_EXPIRY["active_discounts"])

def get_cached_active_discounts() -> Optional[List[Dict]]:
    """Get cached active discounts."""
    return cache_get("active_discounts")

def invalidate_active_discounts_cache():
    """Invalidate active discounts cache when they're modified."""
    return cache_delete("active_discounts")

def cache_invoice_details(invoice_id: int, details: Dict) -> bool:
    """Cache invoice details."""
    key = f"invoice:{invoice_id}"
    return cache_set(key, details, CACHE_EXPIRY["invoice_details"])

def get_cached_invoice_details(invoice_id: int) -> Optional[Dict]:
    """Get cached invoice details."""
    key = f"invoice:{invoice_id}"
    return cache_get(key)

def invalidate_invoice_cache(invoice_id: int) -> bool:
    """Invalidate invoice cache when it's modified."""
    key = f"invoice:{invoice_id}"
    return cache_delete(key)

def cache_user_credit_notes(user_id: int, credit_notes: List[Dict]) -> bool:
    """Cache user credit notes."""
    key = f"user_credit_notes:{user_id}"
    return cache_set(key, credit_notes, CACHE_EXPIRY["user_credit_notes"])

def get_cached_user_credit_notes(user_id: int) -> Optional[List[Dict]]:
    """Get cached user credit notes."""
    key = f"user_credit_notes:{user_id}"
    return cache_get(key)

def invalidate_user_credit_notes_cache(user_id: int) -> bool:
    """Invalidate user credit notes cache when they're modified."""
    key = f"user_credit_notes:{user_id}"
    return cache_delete(key)

# Additional caching functions for billing module

def cache_user_invoices(user_id: int, invoices: List[Dict]) -> bool:
    """Cache all invoices for a user."""
    key = f"user_invoices:{user_id}"
    return cache_set(key, invoices, CACHE_EXPIRY["user_invoices"])

def get_cached_user_invoices(user_id: int) -> Optional[List[Dict]]:
    """Get cached invoices for a user."""
    key = f"user_invoices:{user_id}"
    return cache_get(key)

def invalidate_user_invoices_cache(user_id: int) -> bool:
    """Invalidate user invoices cache when they're modified."""
    key = f"user_invoices:{user_id}"
    return cache_delete(key)

def cache_payment_history(user_id: int, payments: List[Dict]) -> bool:
    """Cache payment history for a user."""
    key = f"payment_history:{user_id}"
    return cache_set(key, payments, CACHE_EXPIRY["payment_history"])

def get_cached_payment_history(user_id: int) -> Optional[List[Dict]]:
    """Get cached payment history for a user."""
    key = f"payment_history:{user_id}"
    return cache_get(key)

def invalidate_payment_history_cache(user_id: int) -> bool:
    """Invalidate payment history cache when it's modified."""
    key = f"payment_history:{user_id}"
    return cache_delete(key)

def cache_billing_statistics(stats: Dict) -> bool:
    """Cache billing statistics."""
    return cache_set("billing_statistics", stats, CACHE_EXPIRY["billing_statistics"])

def get_cached_billing_statistics() -> Optional[Dict]:
    """Get cached billing statistics."""
    return cache_get("billing_statistics")

def invalidate_billing_statistics_cache() -> bool:
    """Invalidate billing statistics cache when underlying data changes."""
    return cache_delete("billing_statistics")

def cache_user_payment_methods(user_id: int, payment_methods: List[Dict]) -> bool:
    """Cache payment methods for a user."""
    key = f"user_payment_methods:{user_id}"
    return cache_set(key, payment_methods, CACHE_EXPIRY["user_payment_methods"])

def get_cached_user_payment_methods(user_id: int) -> Optional[List[Dict]]:
    """Get cached payment methods for a user."""
    key = f"user_payment_methods:{user_id}"
    return cache_get(key)

def invalidate_user_payment_methods_cache(user_id: int) -> bool:
    """Invalidate user payment methods cache when they're modified."""
    key = f"user_payment_methods:{user_id}"
    return cache_delete(key)

def warm_up_cache(db_session) -> Dict[str, int]:
    """
    Warm up the cache with frequently accessed data.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        Dict: Count of items cached by category
    """
    from .models import TaxRate, Discount, User
    
    cache_counts = {
        "tax_rates": 0,
        "active_discounts": 0,
        "user_credit_notes": 0,
    }
    
    # Cache tax rates
    tax_rates = db_session.query(TaxRate).filter(TaxRate.is_default == True).all()
    for tax_rate in tax_rates:
        if cache_tax_rate(tax_rate.country, tax_rate.region, tax_rate.to_dict()):
            cache_counts["tax_rates"] += 1
    
    # Cache active discounts
    from datetime import datetime
    current_date = datetime.utcnow()
    active_discounts = db_session.query(Discount).filter(
        Discount.is_active == True,
        Discount.valid_from <= current_date,
        (Discount.valid_to == None) | (Discount.valid_to >= current_date)
    ).all()
    
    if cache_active_discounts([d.to_dict() for d in active_discounts]):
        cache_counts["active_discounts"] = len(active_discounts)
    
    # Cache credit notes for active users
    active_users = db_session.query(User).filter(User.is_active == True).limit(100).all()
    for user in active_users:
        credit_notes = db_session.query(CreditNote).filter(
            CreditNote.user_id == user.id,
            CreditNote.status.in_(["issued", "partial"])
        ).all()
        
        if credit_notes and cache_user_credit_notes(user.id, [cn.to_dict() for cn in credit_notes]):
            cache_counts["user_credit_notes"] += 1
    
    return cache_counts
