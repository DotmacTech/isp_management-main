#!/usr/bin/env python
"""
HATEOAS Implementation Verification Script

This script makes direct HTTP requests to the API endpoints to verify
that HATEOAS links are correctly implemented in the responses.
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
import argparse
from tabulate import tabulate
from colorama import init, Fore, Style

# Initialize colorama for colored terminal output
init()

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))


class HateoasVerifier:
    """Verifies HATEOAS implementation in API endpoints."""
    
    def __init__(self, base_url, token=None):
        """Initialize with base URL and optional auth token."""
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": base_url,
            "endpoints": []
        }
    
    def get_headers(self):
        """Get request headers including authorization if token is available."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def authenticate(self, username, password):
        """Authenticate and get token."""
        auth_url = f"{self.base_url}/auth/token"
        response = requests.post(
            auth_url,
            data={"username": username, "password": password}
        )
        
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            print(f"{Fore.GREEN}✓ Authentication successful{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Authentication failed: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return False
    
    def verify_endpoint(self, endpoint, expected_links=None):
        """Verify HATEOAS implementation for a specific endpoint."""
        url = f"{self.base_url}{endpoint}"
        print(f"Testing endpoint: {url}")
        
        try:
            response = requests.get(url, headers=self.get_headers())
            
            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "has_hateoas": False,
                "missing_links": [],
                "errors": []
            }
            
            if response.status_code != 200:
                result["errors"].append(f"Request failed with status code {response.status_code}")
                print(f"{Fore.RED}✗ Request failed: {response.status_code}{Style.RESET_ALL}")
                self.results["endpoints"].append(result)
                return False
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                result["errors"].append("Response is not valid JSON")
                print(f"{Fore.RED}✗ Response is not valid JSON{Style.RESET_ALL}")
                self.results["endpoints"].append(result)
                return False
            
            # Check for _links in response
            if "_links" not in data:
                result["errors"].append("Response does not contain _links")
                print(f"{Fore.RED}✗ No _links found in response{Style.RESET_ALL}")
                self.results["endpoints"].append(result)
                return False
            
            result["has_hateoas"] = True
            
            # Check for expected links
            if expected_links:
                for link in expected_links:
                    if link not in data["_links"]:
                        result["missing_links"].append(link)
            
            # Check for items with _links if it's a collection
            if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:
                result["has_item_links"] = all("_links" in item for item in data["items"])
                if not result["has_item_links"]:
                    result["errors"].append("Some items do not have _links")
            
            if result["missing_links"] or result["errors"]:
                print(f"{Fore.YELLOW}⚠ Some expected links are missing or errors occurred{Style.RESET_ALL}")
                for link in result["missing_links"]:
                    print(f"  {Fore.YELLOW}⚠ Missing link: {link}{Style.RESET_ALL}")
                for error in result["errors"]:
                    print(f"  {Fore.RED}✗ Error: {error}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}✓ HATEOAS implementation verified{Style.RESET_ALL}")
            
            self.results["endpoints"].append(result)
            return len(result["missing_links"]) == 0 and len(result["errors"]) == 0
            
        except requests.RequestException as e:
            result["errors"].append(f"Request exception: {str(e)}")
            print(f"{Fore.RED}✗ Request exception: {str(e)}{Style.RESET_ALL}")
            self.results["endpoints"].append(result)
            return False
    
    def verify_all_endpoints(self):
        """Verify HATEOAS implementation for all known endpoints."""
        # Define endpoints to test with their expected links
        endpoints = [
            # Communications module
            {
                "path": "/api/v1/communications/messages",
                "expected_links": ["self", "create"]
            },
            {
                "path": "/api/v1/communications/notifications",
                "expected_links": ["self", "mark_all_as_read"]
            },
            {
                "path": "/api/v1/communications/announcements",
                "expected_links": ["self", "create"]
            },
            {
                "path": "/api/v1/communications/support-tickets",
                "expected_links": ["self", "create"]
            },
            
            # Monitoring module
            {
                "path": "/api/v1/monitoring/health",
                "expected_links": ["self", "metrics", "alerts"]
            },
            {
                "path": "/api/v1/monitoring/metrics",
                "expected_links": ["self", "record"]
            },
            {
                "path": "/api/v1/monitoring/alerts",
                "expected_links": ["self", "create"]
            },
            {
                "path": "/api/v1/monitoring/alert-configurations",
                "expected_links": ["self", "create"]
            },
            {
                "path": "/api/v1/monitoring/alert-history",
                "expected_links": ["self"]
            },
            {
                "path": "/api/v1/monitoring/reports",
                "expected_links": ["self", "generate"]
            },
            {
                "path": "/api/v1/monitoring/dashboards",
                "expected_links": ["self", "create"]
            }
        ]
        
        results = []
        for endpoint in endpoints:
            success = self.verify_endpoint(endpoint["path"], endpoint["expected_links"])
            results.append({
                "endpoint": endpoint["path"],
                "status": "PASS" if success else "FAIL"
            })
            print()  # Add a blank line between endpoints
        
        return results
    
    def save_results(self, output_file=None):
        """Save verification results to a file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = project_root / f"test_reports/hateoas_verification_{timestamp}.json"
        
        # Ensure directory exists
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
    
    def print_summary(self):
        """Print a summary of the verification results."""
        total = len(self.results["endpoints"])
        successful = sum(1 for e in self.results["endpoints"] if e["has_hateoas"] and not e["errors"] and not e["missing_links"])
        
        print("\n" + "=" * 80)
        print(f"HATEOAS VERIFICATION SUMMARY")
        print("-" * 80)
        print(f"Total endpoints tested: {total}")
        print(f"Successfully verified: {successful}")
        print(f"Failed verification: {total - successful}")
        
        # Create a table of results
        table_data = []
        for endpoint in self.results["endpoints"]:
            status = "PASS" if endpoint["has_hateoas"] and not endpoint["errors"] and not endpoint["missing_links"] else "FAIL"
            status_color = Fore.GREEN if status == "PASS" else Fore.RED
            table_data.append([
                endpoint["endpoint"],
                f"{status_color}{status}{Style.RESET_ALL}",
                ", ".join(endpoint["missing_links"]) if endpoint["missing_links"] else "-",
                ", ".join(endpoint["errors"]) if endpoint["errors"] else "-"
            ])
        
        print("\nDetailed Results:")
        print(tabulate(
            table_data,
            headers=["Endpoint", "Status", "Missing Links", "Errors"],
            tablefmt="grid"
        ))
        print("=" * 80)


def main():
    """Main function to run the verification script."""
    parser = argparse.ArgumentParser(description="Verify HATEOAS implementation in API endpoints")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument("--output", help="Output file for results")
    args = parser.parse_args()
    
    print("=" * 80)
    print("ISP Management Platform - HATEOAS Implementation Verification")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {args.base_url}")
    print("-" * 80)
    
    verifier = HateoasVerifier(args.base_url)
    
    # Authenticate if credentials are provided
    if args.username and args.password:
        if not verifier.authenticate(args.username, args.password):
            sys.exit(1)
    else:
        print(f"{Fore.YELLOW}⚠ No authentication credentials provided. Some endpoints may fail.{Style.RESET_ALL}")
    
    # Verify all endpoints
    verifier.verify_all_endpoints()
    
    # Save results
    output_file = args.output
    if output_file:
        verifier.save_results(Path(output_file))
    else:
        verifier.save_results()
    
    # Print summary
    verifier.print_summary()


if __name__ == "__main__":
    main()
