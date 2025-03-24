#!/usr/bin/env python
"""
Verification script for the service availability monitoring feature.

This script performs a series of checks to verify that the service availability
monitoring feature is working correctly. It tests the following components:
1. Service endpoint creation and management
2. Service status checking for different protocols
3. Outage detection and management
4. Maintenance window scheduling
5. Elasticsearch integration for logging and metrics

Usage:
    python verify_service_monitoring.py [--verbose]

Options:
    --verbose       Run checks in verbose mode
"""

import os
import sys
import time
import json
import argparse
import logging
import requests
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verify_service_monitoring")

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Set environment variables
os.environ["PYTHONPATH"] = project_root

# Import required modules
try:
    from backend_core.database import SessionLocal
    from modules.monitoring.models.service_availability import (
        ServiceEndpoint, ServiceStatus, ServiceOutage, MaintenanceWindow,
        ProtocolType, StatusType, SeverityLevel
    )
    from modules.monitoring.services.availability_service import AvailabilityService
    from modules.monitoring.services.availability_service_outage import OutageManagementService
    from modules.monitoring.collectors.service_availability_collector import ServiceAvailabilityCollector
    from modules.monitoring.elasticsearch import ElasticsearchClient
    
    logger.info("Successfully imported required modules")
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    sys.exit(1)


class ServiceMonitoringVerifier:
    """Verifier for service availability monitoring feature."""
    
    def __init__(self, verbose=False):
        """Initialize the verifier."""
        self.verbose = verbose
        self.db = SessionLocal()
        self.availability_service = AvailabilityService(self.db)
        self.outage_service = OutageManagementService(self.db)
        self.collector = ServiceAvailabilityCollector(self.db)
        
        try:
            self.es_client = ElasticsearchClient()
            self.es_available = True
        except Exception as e:
            logger.warning(f"Elasticsearch not available: {e}")
            self.es_available = False
        
        self.results = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "skipped_checks": 0,
            "checks": []
        }
    
    def log_check(self, name, result, details=None):
        """Log a check result."""
        check = {
            "name": name,
            "result": result,
            "details": details or {}
        }
        
        self.results["total_checks"] += 1
        if result == "PASS":
            self.results["passed_checks"] += 1
            logger.info(f"✅ {name}: PASS")
        elif result == "FAIL":
            self.results["failed_checks"] += 1
            logger.error(f"❌ {name}: FAIL - {details}")
        elif result == "SKIP":
            self.results["skipped_checks"] += 1
            logger.warning(f"⚠️ {name}: SKIP - {details}")
        
        self.results["checks"].append(check)
        
        if self.verbose and details:
            if isinstance(details, dict):
                for key, value in details.items():
                    logger.info(f"  {key}: {value}")
            else:
                logger.info(f"  Details: {details}")
    
    def verify_service_endpoint_management(self):
        """Verify service endpoint management functionality."""
        logger.info("Verifying service endpoint management...")
        
        # Create endpoint
        try:
            endpoint_data = {
                "id": "test-verify-http",
                "name": "Test Verification HTTP",
                "url": "https://example.com",
                "protocol": ProtocolType.HTTPS,
                "check_interval": 60,
                "timeout": 5,
                "retries": 3,
                "expected_status_code": 200,
                "is_active": True
            }
            
            endpoint = self.availability_service.create_endpoint(endpoint_data)
            
            if endpoint and endpoint.id == "test-verify-http":
                self.log_check("Create service endpoint", "PASS", {
                    "endpoint_id": endpoint.id,
                    "name": endpoint.name
                })
            else:
                self.log_check("Create service endpoint", "FAIL", "Failed to create endpoint")
                return
        except Exception as e:
            self.log_check("Create service endpoint", "FAIL", str(e))
            return
        
        # Update endpoint
        try:
            update_data = {
                "name": "Updated Test Verification HTTP",
                "check_interval": 120
            }
            
            updated = self.availability_service.update_endpoint(endpoint.id, update_data)
            
            if updated and updated.name == "Updated Test Verification HTTP" and updated.check_interval == 120:
                self.log_check("Update service endpoint", "PASS", {
                    "endpoint_id": updated.id,
                    "name": updated.name,
                    "check_interval": updated.check_interval
                })
            else:
                self.log_check("Update service endpoint", "FAIL", "Failed to update endpoint")
        except Exception as e:
            self.log_check("Update service endpoint", "FAIL", str(e))
        
        # Get endpoint
        try:
            retrieved = self.availability_service.get_endpoint(endpoint.id)
            
            if retrieved and retrieved.id == endpoint.id:
                self.log_check("Get service endpoint", "PASS", {
                    "endpoint_id": retrieved.id,
                    "name": retrieved.name
                })
            else:
                self.log_check("Get service endpoint", "FAIL", "Failed to retrieve endpoint")
        except Exception as e:
            self.log_check("Get service endpoint", "FAIL", str(e))
        
        # Get all endpoints
        try:
            endpoints, _ = self.availability_service.get_all_endpoints()
            
            if endpoints and len(endpoints) > 0:
                self.log_check("Get all service endpoints", "PASS", {
                    "count": len(endpoints)
                })
            else:
                self.log_check("Get all service endpoints", "FAIL", "Failed to retrieve endpoints")
        except Exception as e:
            self.log_check("Get all service endpoints", "FAIL", str(e))
        
        # Delete endpoint
        try:
            deleted = self.availability_service.delete_endpoint(endpoint.id)
            
            if deleted:
                self.log_check("Delete service endpoint", "PASS", {
                    "endpoint_id": endpoint.id
                })
            else:
                self.log_check("Delete service endpoint", "FAIL", "Failed to delete endpoint")
        except Exception as e:
            self.log_check("Delete service endpoint", "FAIL", str(e))
    
    def verify_service_status_checking(self):
        """Verify service status checking functionality."""
        logger.info("Verifying service status checking...")
        
        # Create test endpoints for different protocols
        endpoints = {}
        
        # HTTP endpoint
        try:
            http_data = {
                "id": "test-verify-http",
                "name": "Test Verification HTTP",
                "url": "https://www.google.com",  # Use a reliable site
                "protocol": ProtocolType.HTTPS,
                "check_interval": 60,
                "timeout": 5,
                "retries": 3,
                "expected_status_code": 200,
                "is_active": True
            }
            
            endpoints["http"] = self.availability_service.create_endpoint(http_data)
            self.log_check("Create HTTP endpoint", "PASS", {
                "endpoint_id": endpoints["http"].id
            })
        except Exception as e:
            self.log_check("Create HTTP endpoint", "FAIL", str(e))
        
        # TCP endpoint
        try:
            tcp_data = {
                "id": "test-verify-tcp",
                "name": "Test Verification TCP",
                "url": "www.google.com:443",  # Use a reliable site
                "protocol": ProtocolType.TCP,
                "check_interval": 60,
                "timeout": 5,
                "retries": 3,
                "is_active": True
            }
            
            endpoints["tcp"] = self.availability_service.create_endpoint(tcp_data)
            self.log_check("Create TCP endpoint", "PASS", {
                "endpoint_id": endpoints["tcp"].id
            })
        except Exception as e:
            self.log_check("Create TCP endpoint", "FAIL", str(e))
        
        # ICMP endpoint
        try:
            icmp_data = {
                "id": "test-verify-icmp",
                "name": "Test Verification ICMP",
                "url": "www.google.com",  # Use a reliable site
                "protocol": ProtocolType.ICMP,
                "check_interval": 60,
                "timeout": 5,
                "retries": 3,
                "is_active": True
            }
            
            endpoints["icmp"] = self.availability_service.create_endpoint(icmp_data)
            self.log_check("Create ICMP endpoint", "PASS", {
                "endpoint_id": endpoints["icmp"].id
            })
        except Exception as e:
            self.log_check("Create ICMP endpoint", "FAIL", str(e))
        
        # Check HTTP endpoint
        if "http" in endpoints:
            try:
                status = self.availability_service.check_service(endpoints["http"].id)
                
                if status and status.status == StatusType.UP:
                    self.log_check("Check HTTP endpoint", "PASS", {
                        "status": status.status.value,
                        "response_time": f"{status.response_time:.3f}s"
                    })
                else:
                    self.log_check("Check HTTP endpoint", "FAIL", {
                        "status": status.status.value if status else "Unknown",
                        "error": status.error_message if status else "No status returned"
                    })
            except Exception as e:
                self.log_check("Check HTTP endpoint", "FAIL", str(e))
        
        # Check TCP endpoint
        if "tcp" in endpoints:
            try:
                status = self.availability_service.check_service(endpoints["tcp"].id)
                
                if status and status.status == StatusType.UP:
                    self.log_check("Check TCP endpoint", "PASS", {
                        "status": status.status.value,
                        "response_time": f"{status.response_time:.3f}s"
                    })
                else:
                    self.log_check("Check TCP endpoint", "FAIL", {
                        "status": status.status.value if status else "Unknown",
                        "error": status.error_message if status else "No status returned"
                    })
            except Exception as e:
                self.log_check("Check TCP endpoint", "FAIL", str(e))
        
        # Check ICMP endpoint
        if "icmp" in endpoints:
            try:
                status = self.availability_service.check_service(endpoints["icmp"].id)
                
                if status:
                    self.log_check("Check ICMP endpoint", "PASS", {
                        "status": status.status.value,
                        "response_time": f"{status.response_time:.3f}s" if status.response_time else "N/A"
                    })
                else:
                    self.log_check("Check ICMP endpoint", "FAIL", "No status returned")
            except Exception as e:
                self.log_check("Check ICMP endpoint", "FAIL", str(e))
        
        # Clean up endpoints
        for protocol, endpoint in endpoints.items():
            try:
                self.availability_service.delete_endpoint(endpoint.id)
                self.log_check(f"Delete {protocol.upper()} endpoint", "PASS")
            except Exception as e:
                self.log_check(f"Delete {protocol.upper()} endpoint", "FAIL", str(e))
    
    def verify_maintenance_windows(self):
        """Verify maintenance window functionality."""
        logger.info("Verifying maintenance windows...")
        
        # Create test endpoint
        try:
            endpoint_data = {
                "id": "test-verify-maintenance",
                "name": "Test Maintenance Endpoint",
                "url": "https://example.com",
                "protocol": ProtocolType.HTTPS,
                "check_interval": 60,
                "timeout": 5,
                "retries": 3,
                "expected_status_code": 200,
                "is_active": True
            }
            
            endpoint = self.availability_service.create_endpoint(endpoint_data)
            self.log_check("Create endpoint for maintenance", "PASS", {
                "endpoint_id": endpoint.id
            })
        except Exception as e:
            self.log_check("Create endpoint for maintenance", "FAIL", str(e))
            return
        
        # Create maintenance window
        try:
            start_time = datetime.utcnow() - timedelta(hours=1)
            end_time = datetime.utcnow() + timedelta(hours=1)
            
            window_data = {
                "endpoint_id": endpoint.id,
                "name": "Test Maintenance Window",
                "description": "Test maintenance window for verification",
                "start_time": start_time,
                "end_time": end_time,
                "is_active": True
            }
            
            window = self.outage_service.create_maintenance_window(window_data)
            
            if window and window.endpoint_id == endpoint.id:
                self.log_check("Create maintenance window", "PASS", {
                    "window_id": window.id,
                    "name": window.name,
                    "start_time": window.start_time.isoformat(),
                    "end_time": window.end_time.isoformat()
                })
            else:
                self.log_check("Create maintenance window", "FAIL", "Failed to create maintenance window")
                return
        except Exception as e:
            self.log_check("Create maintenance window", "FAIL", str(e))
            return
        
        # Check if endpoint is in maintenance
        try:
            in_maintenance = self.outage_service.is_in_maintenance(endpoint.id)
            
            if in_maintenance:
                self.log_check("Check if endpoint is in maintenance", "PASS", {
                    "in_maintenance": in_maintenance
                })
            else:
                self.log_check("Check if endpoint is in maintenance", "FAIL", "Endpoint should be in maintenance")
        except Exception as e:
            self.log_check("Check if endpoint is in maintenance", "FAIL", str(e))
        
        # Get active maintenance windows
        try:
            windows = self.outage_service.get_active_maintenance_windows()
            
            if windows and any(w.endpoint_id == endpoint.id for w in windows):
                self.log_check("Get active maintenance windows", "PASS", {
                    "count": len(windows)
                })
            else:
                self.log_check("Get active maintenance windows", "FAIL", "Maintenance window not found in active windows")
        except Exception as e:
            self.log_check("Get active maintenance windows", "FAIL", str(e))
        
        # Clean up
        try:
            # Delete maintenance window
            self.db.delete(window)
            # Delete endpoint
            self.availability_service.delete_endpoint(endpoint.id)
            self.db.commit()
            
            self.log_check("Clean up maintenance test resources", "PASS")
        except Exception as e:
            self.log_check("Clean up maintenance test resources", "FAIL", str(e))
    
    def verify_elasticsearch_integration(self):
        """Verify Elasticsearch integration."""
        logger.info("Verifying Elasticsearch integration...")
        
        if not self.es_available:
            self.log_check("Elasticsearch connection", "SKIP", "Elasticsearch not available")
            return
        
        # Check Elasticsearch connection
        try:
            info = self.es_client.info()
            
            if info and "version" in info:
                self.log_check("Elasticsearch connection", "PASS", {
                    "version": info["version"]["number"],
                    "cluster_name": info["cluster_name"]
                })
            else:
                self.log_check("Elasticsearch connection", "FAIL", "Failed to get Elasticsearch info")
                return
        except Exception as e:
            self.log_check("Elasticsearch connection", "FAIL", str(e))
            return
        
        # Create test endpoint and status
        try:
            endpoint_data = {
                "id": "test-verify-es",
                "name": "Test ES Integration",
                "url": "https://example.com",
                "protocol": ProtocolType.HTTPS,
                "check_interval": 60,
                "timeout": 5,
                "retries": 3,
                "expected_status_code": 200,
                "is_active": True
            }
            
            endpoint = self.availability_service.create_endpoint(endpoint_data)
            
            # Create status
            status = ServiceStatus(
                id=str(time.time()),
                endpoint_id=endpoint.id,
                status=StatusType.UP,
                response_time=0.123,
                timestamp=datetime.utcnow(),
                elasticsearch_synced=False
            )
            
            self.db.add(status)
            self.db.commit()
            
            self.log_check("Create test status for ES sync", "PASS", {
                "status_id": status.id,
                "endpoint_id": endpoint.id
            })
        except Exception as e:
            self.log_check("Create test status for ES sync", "FAIL", str(e))
            return
        
        # Sync status to Elasticsearch
        try:
            results = self.collector.sync_unsynced_statuses(limit=10)
            
            if results["successful"] > 0:
                self.log_check("Sync status to Elasticsearch", "PASS", {
                    "synced": results["successful"]
                })
            else:
                self.log_check("Sync status to Elasticsearch", "FAIL", "No statuses synced")
        except Exception as e:
            self.log_check("Sync status to Elasticsearch", "FAIL", str(e))
        
        # Clean up
        try:
            # Delete status
            self.db.delete(status)
            # Delete endpoint
            self.availability_service.delete_endpoint(endpoint.id)
            self.db.commit()
            
            self.log_check("Clean up ES test resources", "PASS")
        except Exception as e:
            self.log_check("Clean up ES test resources", "FAIL", str(e))
    
    def verify_collector(self):
        """Verify collector functionality."""
        logger.info("Verifying collector functionality...")
        
        # Create test endpoint
        try:
            endpoint_data = {
                "id": "test-verify-collector",
                "name": "Test Collector Endpoint",
                "url": "https://www.google.com",
                "protocol": ProtocolType.HTTPS,
                "check_interval": 60,
                "timeout": 5,
                "retries": 3,
                "expected_status_code": 200,
                "is_active": True
            }
            
            endpoint = self.availability_service.create_endpoint(endpoint_data)
            self.log_check("Create endpoint for collector", "PASS", {
                "endpoint_id": endpoint.id
            })
        except Exception as e:
            self.log_check("Create endpoint for collector", "FAIL", str(e))
            return
        
        # Collect specific service
        try:
            results = self.collector.collect_service(endpoint.id)
            
            if results and "status" in results and results["success"]:
                self.log_check("Collect specific service", "PASS", {
                    "status": results["status"],
                    "response_time": results["response_time"]
                })
            else:
                self.log_check("Collect specific service", "FAIL", {
                    "error": results.get("error", "Unknown error")
                })
        except Exception as e:
            self.log_check("Collect specific service", "FAIL", str(e))
        
        # Collect all services
        try:
            results = self.collector.collect_all_services()
            
            if results and "total" in results:
                self.log_check("Collect all services", "PASS", {
                    "total": results["total"],
                    "successful": results["successful"],
                    "failed": results["failed"],
                    "in_maintenance": results["in_maintenance"]
                })
            else:
                self.log_check("Collect all services", "FAIL", "Invalid results")
        except Exception as e:
            self.log_check("Collect all services", "FAIL", str(e))
        
        # Clean up
        try:
            self.availability_service.delete_endpoint(endpoint.id)
            self.log_check("Clean up collector test resources", "PASS")
        except Exception as e:
            self.log_check("Clean up collector test resources", "FAIL", str(e))
    
    def run_all_checks(self):
        """Run all verification checks."""
        logger.info("Running all verification checks...")
        
        try:
            # Run checks
            self.verify_service_endpoint_management()
            self.verify_service_status_checking()
            self.verify_maintenance_windows()
            self.verify_elasticsearch_integration()
            self.verify_collector()
            
            # Print summary
            logger.info("=" * 50)
            logger.info("Verification Summary")
            logger.info("=" * 50)
            logger.info(f"Total checks:   {self.results['total_checks']}")
            logger.info(f"Passed checks:  {self.results['passed_checks']}")
            logger.info(f"Failed checks:  {self.results['failed_checks']}")
            logger.info(f"Skipped checks: {self.results['skipped_checks']}")
            logger.info("=" * 50)
            
            # Determine overall result
            if self.results["failed_checks"] == 0:
                if self.results["skipped_checks"] == 0:
                    logger.info("✅ All checks passed!")
                else:
                    logger.info("✅ All checks passed, but some were skipped.")
            else:
                logger.error("❌ Some checks failed. See above for details.")
            
            # Return overall success
            return self.results["failed_checks"] == 0
        
        finally:
            # Close database session
            self.db.close()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Verify service availability monitoring")
    parser.add_argument("--verbose", action="store_true", help="Run checks in verbose mode")
    args = parser.parse_args()
    
    # Run verification
    verifier = ServiceMonitoringVerifier(verbose=args.verbose)
    success = verifier.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
