#!/usr/bin/env python
"""
Cache Management Utility

This script provides utilities for managing the Redis cache in the ISP Management Platform.
It allows for viewing cache statistics, clearing specific cache types, and warming up
the cache with frequently accessed data.
"""
import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from isp_management.backend_core.cache import redis_client
from isp_management.backend_core.database import SessionLocal
from isp_management.modules.billing.services import BillingService
from isp_management.backend_core.models import Invoice, TaxRate, Discount, CreditNote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cache_management.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cache_management")

class CacheManager:
    """Utility for managing Redis cache."""
    
    def __init__(self):
        """Initialize the cache manager."""
        self.db = SessionLocal()
        self.billing_service = BillingService(self.db)
        
        # Define cache key patterns
        self.cache_patterns = {
            "tax_rates": "tax_rate:*",
            "active_discounts": "active_discounts",
            "invoices": "invoice:*",
            "user_credit_notes": "user_credit_notes:*",
            "all": "*"
        }
    
    def __del__(self):
        """Clean up resources."""
        self.db.close()
    
    def get_cache_stats(self):
        """Get cache statistics."""
        stats = {
            "total_keys": 0,
            "memory_used": 0,
            "key_counts": {},
            "expiry_stats": {
                "expired": 0,
                "ttl_stats": {
                    "no_expiry": 0,
                    "less_than_hour": 0,
                    "less_than_day": 0,
                    "more_than_day": 0
                }
            }
        }
        
        # Get total memory usage
        info = redis_client.info()
        stats["memory_used"] = info.get("used_memory_human", "N/A")
        
        # Count keys by pattern
        for cache_type, pattern in self.cache_patterns.items():
            if cache_type == "all":
                continue
                
            keys = redis_client.keys(pattern)
            stats["key_counts"][cache_type] = len(keys)
            stats["total_keys"] += len(keys)
            
            # Check expiry for each key
            for key in keys:
                ttl = redis_client.ttl(key)
                if ttl == -1:  # No expiry
                    stats["expiry_stats"]["ttl_stats"]["no_expiry"] += 1
                elif ttl == -2:  # Expired
                    stats["expiry_stats"]["expired"] += 1
                elif ttl < 3600:  # Less than an hour
                    stats["expiry_stats"]["ttl_stats"]["less_than_hour"] += 1
                elif ttl < 86400:  # Less than a day
                    stats["expiry_stats"]["ttl_stats"]["less_than_day"] += 1
                else:  # More than a day
                    stats["expiry_stats"]["ttl_stats"]["more_than_day"] += 1
        
        return stats
    
    def clear_cache(self, cache_type="all"):
        """Clear cache by type."""
        if cache_type not in self.cache_patterns:
            logger.error(f"Invalid cache type: {cache_type}")
            return False
        
        pattern = self.cache_patterns[cache_type]
        
        if pattern == "*":
            redis_client.flushdb()
            logger.info("Cleared all cache entries")
            return True
        
        # Get keys matching pattern
        keys = redis_client.keys(pattern)
        if not keys:
            logger.info(f"No keys found matching pattern: {pattern}")
            return True
        
        # Delete keys
        deleted = redis_client.delete(*keys)
        logger.info(f"Deleted {deleted} cache entries of type: {cache_type}")
        return True
    
    def warm_up_cache(self):
        """Warm up the cache with frequently accessed data."""
        logger.info("Warming up cache...")
        start_time = time.time()
        
        # 1. Cache tax rates for common countries
        self._warm_up_tax_rates()
        
        # 2. Cache active discounts
        self._warm_up_active_discounts()
        
        # 3. Cache recent invoices
        self._warm_up_recent_invoices()
        
        # 4. Cache user credit notes for users with recent activity
        self._warm_up_user_credit_notes()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Cache warm-up completed in {elapsed_time:.2f} seconds")
    
    def _warm_up_tax_rates(self):
        """Warm up tax rates cache."""
        logger.info("Warming up tax rates cache...")
        
        # Get all tax rates
        tax_rates = self.db.query(TaxRate).all()
        
        # Cache each tax rate
        for tax_rate in tax_rates:
            self.billing_service.get_applicable_tax_rate(tax_rate.country, tax_rate.region or "")
        
        logger.info(f"Cached {len(tax_rates)} tax rates")
    
    def _warm_up_active_discounts(self):
        """Warm up active discounts cache."""
        logger.info("Warming up active discounts cache...")
        
        # Cache active discounts
        discounts = self.billing_service.get_active_discounts()
        
        logger.info(f"Cached {len(discounts)} active discounts")
    
    def _warm_up_recent_invoices(self):
        """Warm up recent invoices cache."""
        logger.info("Warming up recent invoices cache...")
        
        # Get recent invoices (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_invoices = self.db.query(Invoice).filter(
            Invoice.created_at >= thirty_days_ago
        ).order_by(Invoice.created_at.desc()).limit(100).all()
        
        # Cache each invoice
        for invoice in recent_invoices:
            self.billing_service.get_invoice_details(invoice.id)
        
        logger.info(f"Cached {len(recent_invoices)} recent invoices")
    
    def _warm_up_user_credit_notes(self):
        """Warm up user credit notes cache."""
        logger.info("Warming up user credit notes cache...")
        
        # Get users with active credit notes
        users_with_credit_notes = self.db.query(CreditNote.user_id).filter(
            CreditNote.status == "issued",
            CreditNote.remaining_amount > 0
        ).distinct().limit(50).all()
        
        # Cache credit notes for each user
        for (user_id,) in users_with_credit_notes:
            self.billing_service.get_user_credit_notes(user_id)
        
        logger.info(f"Cached credit notes for {len(users_with_credit_notes)} users")
    
    def print_cache_stats(self):
        """Print cache statistics."""
        stats = self.get_cache_stats()
        
        logger.info("=" * 80)
        logger.info("REDIS CACHE STATISTICS")
        logger.info("=" * 80)
        
        logger.info(f"Total Keys: {stats['total_keys']}")
        logger.info(f"Memory Used: {stats['memory_used']}")
        
        logger.info("\nKey Counts by Type:")
        for cache_type, count in stats['key_counts'].items():
            logger.info(f"  {cache_type}: {count}")
        
        logger.info("\nExpiry Statistics:")
        logger.info(f"  Expired Keys: {stats['expiry_stats']['expired']}")
        logger.info("  TTL Distribution:")
        for ttl_range, count in stats['expiry_stats']['ttl_stats'].items():
            logger.info(f"    {ttl_range}: {count}")
        
        logger.info("\n" + "=" * 80)
        
        # Save stats to JSON file
        with open("cache_stats.json", "w") as f:
            json.dump(stats, f, indent=2)
        
        logger.info("Statistics saved to cache_stats.json")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Redis Cache Management Utility")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show cache statistics")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear cache")
    clear_parser.add_argument("--type", choices=["tax_rates", "active_discounts", "invoices", "user_credit_notes", "all"],
                             default="all", help="Type of cache to clear")
    
    # Warm-up command
    warmup_parser = subparsers.add_parser("warmup", help="Warm up cache with frequently accessed data")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        cache_manager = CacheManager()
        
        if args.command == "stats":
            cache_manager.print_cache_stats()
        elif args.command == "clear":
            cache_manager.clear_cache(args.type)
        elif args.command == "warmup":
            cache_manager.warm_up_cache()
        
    except Exception as e:
        logger.error(f"Error executing command: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
