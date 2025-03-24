#!/usr/bin/env python
"""
Cache Performance Monitoring Script

This script monitors the performance of the Redis caching implementation
in the ISP Management Platform. It tracks cache hit rates, miss rates,
and average response times for cached vs. non-cached operations.
"""
import os
import sys
import time
import json
import logging
import argparse
import datetime
from decimal import Decimal
from collections import defaultdict
import statistics

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from isp_management.backend_core.cache import redis_client
from isp_management.backend_core.database import SessionLocal
from isp_management.modules.billing.services import BillingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cache_performance.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cache_monitor")

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

class CachePerformanceMonitor:
    """Monitor cache performance metrics."""
    
    def __init__(self):
        """Initialize the monitor."""
        self.db = SessionLocal()
        self.billing_service = BillingService(self.db)
        self.metrics = {
            "tax_rates": {"hits": 0, "misses": 0, "cached_times": [], "db_times": []},
            "active_discounts": {"hits": 0, "misses": 0, "cached_times": [], "db_times": []},
            "invoice_details": {"hits": 0, "misses": 0, "cached_times": [], "db_times": []},
            "user_credit_notes": {"hits": 0, "misses": 0, "cached_times": [], "db_times": []},
        }
        
    def __del__(self):
        """Clean up resources."""
        self.db.close()
    
    def _time_operation(self, operation, *args, **kwargs):
        """Time an operation and return the result and elapsed time."""
        start_time = time.time()
        result = operation(*args, **kwargs)
        elapsed_time = time.time() - start_time
        return result, elapsed_time
    
    def test_tax_rate_performance(self, iterations=100):
        """Test tax rate caching performance."""
        logger.info(f"Testing tax rate caching performance ({iterations} iterations)...")
        
        # Get a list of country/region pairs to test
        countries = ["US", "GB", "CA", "AU", "DE"]
        regions = {
            "US": ["CA", "NY", "TX", "FL", "IL"],
            "GB": ["", "London", "Scotland", "Wales", "Northern Ireland"],
            "CA": ["ON", "BC", "QC", "AB", "NS"],
            "AU": ["NSW", "VIC", "QLD", "WA", "SA"],
            "DE": ["", "Bavaria", "Berlin", "Hesse", "Saxony"]
        }
        
        # Clear cache for test countries/regions
        for country in countries:
            for region in regions.get(country, [""]):
                redis_client.delete(f"tax_rate:{country}:{region}")
        
        for i in range(iterations):
            # Select a country/region pair
            country = countries[i % len(countries)]
            region = regions[country][i % len(regions[country])]
            
            # First call (potential cache miss)
            result, db_time = self._time_operation(
                self.billing_service.get_applicable_tax_rate, country, region
            )
            
            # Check if result is in cache now
            cache_key = f"tax_rate:{country}:{region}"
            cached_data = redis_client.get(cache_key)
            
            if cached_data:
                # Second call (should be cache hit)
                _, cached_time = self._time_operation(
                    self.billing_service.get_applicable_tax_rate, country, region
                )
                self.metrics["tax_rates"]["hits"] += 1
                self.metrics["tax_rates"]["cached_times"].append(cached_time)
            else:
                self.metrics["tax_rates"]["misses"] += 1
            
            self.metrics["tax_rates"]["db_times"].append(db_time)
            
            # Occasionally clear cache to test miss scenarios
            if i % 10 == 0:
                redis_client.delete(cache_key)
    
    def test_active_discounts_performance(self, iterations=50):
        """Test active discounts caching performance."""
        logger.info(f"Testing active discounts caching performance ({iterations} iterations)...")
        
        # Clear cache
        redis_client.delete("active_discounts")
        
        for i in range(iterations):
            # First call (potential cache miss)
            result, db_time = self._time_operation(
                self.billing_service.get_active_discounts
            )
            
            # Check if result is in cache now
            cached_data = redis_client.get("active_discounts")
            
            if cached_data:
                # Second call (should be cache hit)
                _, cached_time = self._time_operation(
                    self.billing_service.get_active_discounts
                )
                self.metrics["active_discounts"]["hits"] += 1
                self.metrics["active_discounts"]["cached_times"].append(cached_time)
            else:
                self.metrics["active_discounts"]["misses"] += 1
            
            self.metrics["active_discounts"]["db_times"].append(db_time)
            
            # Occasionally clear cache to test miss scenarios
            if i % 5 == 0:
                redis_client.delete("active_discounts")
    
    def test_invoice_details_performance(self, iterations=50):
        """Test invoice details caching performance."""
        logger.info(f"Testing invoice details caching performance ({iterations} iterations)...")
        
        # Get a list of invoice IDs to test
        invoice_ids = [
            invoice.id for invoice in self.db.query(
                "SELECT id FROM invoices ORDER BY id DESC LIMIT 20"
            ).all()
        ]
        
        if not invoice_ids:
            logger.warning("No invoices found for testing")
            return
        
        # Clear cache for test invoices
        for invoice_id in invoice_ids:
            redis_client.delete(f"invoice:{invoice_id}")
        
        for i in range(iterations):
            # Select an invoice ID
            invoice_id = invoice_ids[i % len(invoice_ids)]
            
            # First call (potential cache miss)
            result, db_time = self._time_operation(
                self.billing_service.get_invoice_details, invoice_id
            )
            
            # Check if result is in cache now
            cache_key = f"invoice:{invoice_id}"
            cached_data = redis_client.get(cache_key)
            
            if cached_data:
                # Second call (should be cache hit)
                _, cached_time = self._time_operation(
                    self.billing_service.get_invoice_details, invoice_id
                )
                self.metrics["invoice_details"]["hits"] += 1
                self.metrics["invoice_details"]["cached_times"].append(cached_time)
            else:
                self.metrics["invoice_details"]["misses"] += 1
            
            self.metrics["invoice_details"]["db_times"].append(db_time)
            
            # Occasionally clear cache to test miss scenarios
            if i % 5 == 0:
                redis_client.delete(cache_key)
    
    def test_user_credit_notes_performance(self, iterations=50):
        """Test user credit notes caching performance."""
        logger.info(f"Testing user credit notes caching performance ({iterations} iterations)...")
        
        # Get a list of user IDs to test
        user_ids = [
            user_id for user_id in self.db.query(
                "SELECT DISTINCT user_id FROM credit_notes ORDER BY user_id LIMIT 10"
            ).all()
        ]
        
        if not user_ids:
            logger.warning("No credit notes found for testing")
            return
        
        # Clear cache for test users
        for user_id in user_ids:
            redis_client.delete(f"user_credit_notes:{user_id}")
        
        for i in range(iterations):
            # Select a user ID
            user_id = user_ids[i % len(user_ids)]
            
            # First call (potential cache miss)
            result, db_time = self._time_operation(
                self.billing_service.get_user_credit_notes, user_id
            )
            
            # Check if result is in cache now
            cache_key = f"user_credit_notes:{user_id}"
            cached_data = redis_client.get(cache_key)
            
            if cached_data:
                # Second call (should be cache hit)
                _, cached_time = self._time_operation(
                    self.billing_service.get_user_credit_notes, user_id
                )
                self.metrics["user_credit_notes"]["hits"] += 1
                self.metrics["user_credit_notes"]["cached_times"].append(cached_time)
            else:
                self.metrics["user_credit_notes"]["misses"] += 1
            
            self.metrics["user_credit_notes"]["db_times"].append(db_time)
            
            # Occasionally clear cache to test miss scenarios
            if i % 5 == 0:
                redis_client.delete(cache_key)
    
    def run_all_tests(self):
        """Run all performance tests."""
        self.test_tax_rate_performance()
        self.test_active_discounts_performance()
        self.test_invoice_details_performance()
        self.test_user_credit_notes_performance()
    
    def calculate_statistics(self):
        """Calculate statistics from collected metrics."""
        stats = {}
        
        for category, data in self.metrics.items():
            total_requests = data["hits"] + data["misses"]
            hit_rate = (data["hits"] / total_requests) * 100 if total_requests > 0 else 0
            
            cached_avg = statistics.mean(data["cached_times"]) if data["cached_times"] else 0
            db_avg = statistics.mean(data["db_times"]) if data["db_times"] else 0
            
            performance_improvement = ((db_avg - cached_avg) / db_avg) * 100 if db_avg > 0 else 0
            
            stats[category] = {
                "total_requests": total_requests,
                "hit_rate": hit_rate,
                "miss_rate": 100 - hit_rate,
                "avg_cached_time": cached_avg,
                "avg_db_time": db_avg,
                "performance_improvement": performance_improvement
            }
        
        return stats
    
    def print_report(self):
        """Print a performance report."""
        stats = self.calculate_statistics()
        
        logger.info("=" * 80)
        logger.info("CACHE PERFORMANCE REPORT")
        logger.info("=" * 80)
        
        for category, data in stats.items():
            logger.info(f"\n{category.upper()} CACHE PERFORMANCE:")
            logger.info(f"  Total Requests: {data['total_requests']}")
            logger.info(f"  Hit Rate: {data['hit_rate']:.2f}%")
            logger.info(f"  Miss Rate: {data['miss_rate']:.2f}%")
            logger.info(f"  Average Cached Response Time: {data['avg_cached_time'] * 1000:.2f} ms")
            logger.info(f"  Average Database Response Time: {data['avg_db_time'] * 1000:.2f} ms")
            logger.info(f"  Performance Improvement: {data['performance_improvement']:.2f}%")
        
        logger.info("\n" + "=" * 80)
        
        # Save report to JSON file
        with open("cache_performance_report.json", "w") as f:
            json.dump(stats, f, indent=2, cls=DecimalEncoder)
        
        logger.info("Report saved to cache_performance_report.json")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Monitor cache performance")
    parser.add_argument("--iterations", type=int, default=50, 
                        help="Number of iterations for each test")
    args = parser.parse_args()
    
    try:
        monitor = CachePerformanceMonitor()
        monitor.run_all_tests()
        monitor.print_report()
    except Exception as e:
        logger.error(f"Error running performance tests: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
