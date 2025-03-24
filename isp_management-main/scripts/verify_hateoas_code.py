#!/usr/bin/env python
"""
HATEOAS Code Verification Script

This script analyzes the codebase to verify that HATEOAS has been properly
implemented in the communications and monitoring modules.
"""

import os
import sys
import re
from pathlib import Path
import json
from datetime import datetime
from colorama import init, Fore, Style

# Initialize colorama for colored terminal output
init()

# Define the project root
project_root = Path(__file__).parent.parent.absolute()


def scan_file_for_hateoas(file_path):
    """
    Scan a file for HATEOAS implementation patterns.
    
    Returns:
        dict: Information about HATEOAS implementation in the file
    """
    result = {
        "file": str(file_path),
        "has_hateoas_imports": False,
        "has_resource_links": False,
        "has_action_links": False,
        "has_links_in_response": False,
        "endpoint_count": 0,
        "hateoas_endpoint_count": 0,
        "endpoints": []
    }
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Check for HATEOAS imports
            if re.search(r'from\s+backend_core\.utils\.hateoas\s+import', content):
                result["has_hateoas_imports"] = True
            
            # Check for resource links usage
            if re.search(r'add_resource_links\s*\(', content):
                result["has_resource_links"] = True
            
            # Check for action links usage
            if re.search(r'add_action_links\s*\(', content):
                result["has_action_links"] = True
            
            # Check for _links in response
            if re.search(r'["\']\s*_links\s*["\']', content):
                result["has_links_in_response"] = True
            
            # Count endpoints (FastAPI route decorators)
            endpoints = re.findall(r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', content)
            result["endpoint_count"] = len(endpoints)
            
            # For each endpoint, check if it has HATEOAS
            for method, path in endpoints:
                endpoint_info = {
                    "method": method.upper(),
                    "path": path,
                    "has_hateoas": False
                }
                
                # Find the function associated with this endpoint
                endpoint_func_match = re.search(
                    rf'@router\.{method}\s*\(\s*["\']({re.escape(path)})["\'][^\n]*\)\s*\n\s*async\s+def\s+([^\(]+)',
                    content
                )
                
                if endpoint_func_match:
                    func_name = endpoint_func_match.group(2).strip()
                    endpoint_info["function"] = func_name
                    
                    # Find the function body
                    func_body_match = re.search(
                        rf'async\s+def\s+{re.escape(func_name)}\s*\([^\)]*\)\s*:([^@]*?)(?=\n\s*(?:async\s+def|\Z))',
                        content,
                        re.DOTALL
                    )
                    
                    if func_body_match:
                        func_body = func_body_match.group(1)
                        
                        # Check if the function uses HATEOAS
                        if (re.search(r'add_resource_links\s*\(', func_body) or 
                            re.search(r'add_action_links\s*\(', func_body)):
                            endpoint_info["has_hateoas"] = True
                            result["hateoas_endpoint_count"] += 1
                
                result["endpoints"].append(endpoint_info)
            
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
    
    return result


def scan_directory(directory_path, pattern="endpoints.py"):
    """
    Scan a directory for files matching the pattern and check for HATEOAS implementation.
    
    Args:
        directory_path: Path to the directory to scan
        pattern: File pattern to match
        
    Returns:
        list: Results of scanning each file
    """
    results = []
    
    try:
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file == pattern:
                    file_path = Path(root) / file
                    result = scan_file_for_hateoas(file_path)
                    results.append(result)
    except Exception as e:
        print(f"Error scanning directory {directory_path}: {e}")
    
    return results


def print_results(results):
    """Print the results of the HATEOAS verification."""
    print("\n" + "=" * 80)
    print("HATEOAS IMPLEMENTATION VERIFICATION RESULTS")
    print("=" * 80)
    
    total_endpoints = 0
    total_hateoas_endpoints = 0
    
    for result in results:
        relative_path = Path(result["file"]).relative_to(project_root)
        print(f"\nFile: {Fore.CYAN}{relative_path}{Style.RESET_ALL}")
        
        # Print HATEOAS implementation status
        hateoas_status = "IMPLEMENTED" if (result["has_hateoas_imports"] and 
                                          (result["has_resource_links"] or result["has_action_links"])) else "NOT IMPLEMENTED"
        status_color = Fore.GREEN if hateoas_status == "IMPLEMENTED" else Fore.RED
        print(f"HATEOAS Status: {status_color}{hateoas_status}{Style.RESET_ALL}")
        
        # Print implementation details
        print(f"  - HATEOAS Imports: {Fore.GREEN if result['has_hateoas_imports'] else Fore.RED}{'✓' if result['has_hateoas_imports'] else '✗'}{Style.RESET_ALL}")
        print(f"  - Resource Links: {Fore.GREEN if result['has_resource_links'] else Fore.RED}{'✓' if result['has_resource_links'] else '✗'}{Style.RESET_ALL}")
        print(f"  - Action Links: {Fore.GREEN if result['has_action_links'] else Fore.RED}{'✓' if result['has_action_links'] else '✗'}{Style.RESET_ALL}")
        print(f"  - Links in Response: {Fore.GREEN if result['has_links_in_response'] else Fore.RED}{'✓' if result['has_links_in_response'] else '✗'}{Style.RESET_ALL}")
        
        # Print endpoint statistics
        print(f"  - Endpoints: {result['endpoint_count']}")
        print(f"  - Endpoints with HATEOAS: {result['hateoas_endpoint_count']} ({int(result['hateoas_endpoint_count']/max(1, result['endpoint_count'])*100)}%)")
        
        # Update totals
        total_endpoints += result["endpoint_count"]
        total_hateoas_endpoints += result["hateoas_endpoint_count"]
        
        # Print endpoint details
        if result["endpoints"]:
            print("\n  Endpoint Details:")
            for endpoint in result["endpoints"]:
                status_color = Fore.GREEN if endpoint["has_hateoas"] else Fore.RED
                status_symbol = "✓" if endpoint["has_hateoas"] else "✗"
                print(f"    - {endpoint['method']} {endpoint['path']}: {status_color}{status_symbol}{Style.RESET_ALL}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"Total Files Scanned: {len(results)}")
    print(f"Total Endpoints: {total_endpoints}")
    print(f"Endpoints with HATEOAS: {total_hateoas_endpoints} ({int(total_hateoas_endpoints/max(1, total_endpoints)*100)}%)")
    
    # Overall assessment
    if total_hateoas_endpoints > 0:
        coverage_percentage = total_hateoas_endpoints / max(1, total_endpoints) * 100
        if coverage_percentage >= 90:
            assessment = f"{Fore.GREEN}EXCELLENT{Style.RESET_ALL} - Over 90% of endpoints have HATEOAS"
        elif coverage_percentage >= 75:
            assessment = f"{Fore.YELLOW}GOOD{Style.RESET_ALL} - Over 75% of endpoints have HATEOAS"
        elif coverage_percentage >= 50:
            assessment = f"{Fore.YELLOW}FAIR{Style.RESET_ALL} - Over 50% of endpoints have HATEOAS"
        else:
            assessment = f"{Fore.RED}NEEDS IMPROVEMENT{Style.RESET_ALL} - Less than 50% of endpoints have HATEOAS"
    else:
        assessment = f"{Fore.RED}NOT IMPLEMENTED{Style.RESET_ALL} - No endpoints have HATEOAS"
    
    print(f"Overall Assessment: {assessment}")
    print("=" * 80)


def save_results(results, output_file=None):
    """Save the results to a JSON file."""
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = project_root / "test_reports"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"hateoas_verification_{timestamp}.json"
    
    # Convert results to a serializable format
    serializable_results = []
    for result in results:
        serializable_result = result.copy()
        serializable_result["file"] = str(serializable_result["file"])
        serializable_results.append(serializable_result)
    
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": serializable_results
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


def main():
    """Main function to run the verification script."""
    print("=" * 80)
    print("ISP Management Platform - HATEOAS Code Verification")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    # Scan communications module
    print(f"\nScanning communications module...")
    communications_results = scan_directory(project_root / "modules" / "communications")
    
    # Scan monitoring module
    print(f"Scanning monitoring module...")
    monitoring_results = scan_directory(project_root / "modules" / "monitoring")
    
    # Combine results
    all_results = communications_results + monitoring_results
    
    # Print and save results
    print_results(all_results)
    save_results(all_results)


if __name__ == "__main__":
    main()
