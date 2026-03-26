# test_runner.py
"""
Automated test execution and reporting for the workspace.
Runs pytest and outputs results to a log file.
"""
import subprocess
import os

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))


def run_tests():
    result = subprocess.run(['pytest', '--maxfail=5', '--disable-warnings', '--tb=short'], capture_output=True, text=True)
    log_path = os.path.join(WORKSPACE_ROOT, 'test_results.log')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        f.write('\n')
        f.write(result.stderr)
    print(f"Test results written to {log_path}")

# Example usage:
# run_tests()
