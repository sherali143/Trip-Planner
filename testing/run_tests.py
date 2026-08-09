"""
Test Runner for Trip Planner
Runs all tests for multiple iterations and logs results.
"""
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess
import sys
import json
from datetime import datetime
from pathlib import Path

def run_tests(num_iterations: int = 3):
    """Run tests for specified number of iterations."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "iterations": num_iterations,
        "runs": []
    }
    
    print(f"=" * 60)
    print(f"Running tests for {num_iterations} iterations")
    print(f"=" * 60)
    
    for i in range(1, num_iterations + 1):
        print(f"\n--- Iteration {i}/{num_iterations} ---")
        
        run_result = {
            "iteration": i,
            "tests": {}
        }
        
        # Run each test file separately for better tracking.
        # These pointed at "tests/", but the directory is "testing/" — so every
        # subprocess exited "file or directory not found" and the runner
        # reported zeros while looking like it had run.
        test_files = [
            "testing/test_calculator.py",
            "testing/test_itinerary_validator.py",
            "testing/test_budget_validation.py",
            "testing/test_mcp_servers.py",
            "testing/test_mcp_integration.py",
        ]
        
        for test_file in test_files:
            test_name = Path(test_file).stem
            print(f"  Running {test_name}...")
            
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                # Parse output
                output = result.stdout + result.stderr
                
                # Count passed/failed
                passed = output.count(" PASSED")
                failed = output.count(" FAILED")
                errors = output.count(" ERROR")
                
                run_result["tests"][test_name] = {
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "exit_code": result.returncode,
                    "output_snippet": output[-500:] if len(output) > 500 else output
                }
                
                status = "✅" if result.returncode == 0 else "❌"
                print(f"    {status} {test_name}: {passed} passed, {failed} failed, {errors} errors")
                
            except subprocess.TimeoutExpired:
                run_result["tests"][test_name] = {
                    "passed": 0,
                    "failed": 0,
                    "errors": 1,
                    "exit_code": -1,
                    "output_snippet": "TIMEOUT"
                }
                print(f"    ⏱️ {test_name}: TIMEOUT")
            
            except Exception as e:
                run_result["tests"][test_name] = {
                    "passed": 0,
                    "failed": 0,
                    "errors": 1, 
                    "exit_code": -1,
                    "output_snippet": str(e)
                }
                print(f"    ❌ {test_name}: ERROR - {e}")
        
        results["runs"].append(run_result)
    
    # Calculate summary
    total_passed = sum(
        sum(t["passed"] for t in run["tests"].values())
        for run in results["runs"]
    )
    total_failed = sum(
        sum(t["failed"] for t in run["tests"].values())
        for run in results["runs"]
    )
    total_errors = sum(
        sum(t["errors"] for t in run["tests"].values())
        for run in results["runs"]
    )
    
    results["summary"] = {
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_errors": total_errors,
        "success_rate": f"{total_passed / max(1, total_passed + total_failed) * 100:.1f}%"
    }
    
    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_failed}")
    print(f"Total Errors: {total_errors}")
    print(f"Success Rate: {results['summary']['success_rate']}")
    print(f"{'=' * 60}")
    
    # Save results to file
    output_file = "test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--iterations", type=int, default=3)
    args = parser.parse_args()
    
    run_tests(args.iterations)

