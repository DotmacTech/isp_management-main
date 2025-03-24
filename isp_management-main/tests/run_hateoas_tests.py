#!/usr/bin/env python
"""
HATEOAS Implementation Test Runner

This script runs comprehensive tests to verify that HATEOAS is correctly
implemented across all API endpoints in the ISP Management Platform.
"""

import os
import sys
import pytest
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))


def run_tests():
    """Run all HATEOAS implementation tests and generate a report."""
    print("=" * 80)
    print("ISP Management Platform - HATEOAS Implementation Test Runner")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    # Create output directory for test reports if it doesn't exist
    reports_dir = project_root / "test_reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Generate report filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = reports_dir / f"hateoas_test_report_{timestamp}.json"
    
    # Modules to test
    modules = ["communications", "monitoring"]
    
    # Store test results
    results = {
        "summary": {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
        },
        "modules": {}
    }
    
    # Run tests for each module
    for module in modules:
        print(f"\nTesting HATEOAS implementation in {module.upper()} module...")
        
        # Path to test file
        test_path = f"tests/{module}/test_hateoas_implementation.py"
        
        # Run pytest for the module
        exit_code = pytest.main([
            test_path,
            "-v",
            f"--junitxml=test_reports/{module}_hateoas_results.xml"
        ])
        
        # Collect test results
        if os.path.exists(f"test_reports/{module}_hateoas_results.xml"):
            import xml.etree.ElementTree as ET
            tree = ET.parse(f"test_reports/{module}_hateoas_results.xml")
            root = tree.getroot()
            
            # Extract test counts
            testsuite = root.find("testsuite")
            if testsuite is not None:
                total = int(testsuite.get("tests", 0))
                failures = int(testsuite.get("failures", 0))
                errors = int(testsuite.get("errors", 0))
                skipped = int(testsuite.get("skipped", 0))
                passed = total - failures - errors - skipped
                
                # Update module results
                results["modules"][module] = {
                    "total": total,
                    "passed": passed,
                    "failed": failures,
                    "errors": errors,
                    "skipped": skipped,
                    "status": "PASSED" if failures == 0 and errors == 0 else "FAILED"
                }
                
                # Update summary
                results["summary"]["total_tests"] += total
                results["summary"]["passed"] += passed
                results["summary"]["failed"] += failures
                results["summary"]["errors"] += errors
                results["summary"]["skipped"] += skipped
                
                # Print module results
                print(f"  Total tests: {total}")
                print(f"  Passed: {passed}")
                print(f"  Failed: {failures}")
                print(f"  Errors: {errors}")
                print(f"  Skipped: {skipped}")
                print(f"  Status: {'PASSED' if failures == 0 and errors == 0 else 'FAILED'}")
    
    # Calculate overall status
    results["summary"]["status"] = "PASSED" if results["summary"]["failed"] == 0 and results["summary"]["errors"] == 0 else "FAILED"
    
    # Save results to file
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Errors: {results['summary']['errors']}")
    print(f"Skipped: {results['summary']['skipped']}")
    print(f"Overall status: {results['summary']['status']}")
    print("-" * 80)
    print(f"Detailed report saved to: {report_file}")
    print("=" * 80)
    
    return results["summary"]["status"] == "PASSED"


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
