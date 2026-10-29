import subprocess
import sys
from pathlib import Path

def test_api_enquiry_node_unit_tests():
    """Execute the Node.js unit test suite for /api/enquiry."""
    test_file = Path(__file__).parent / "test_enquiry_handler.js"
    res = subprocess.run([sys.executable.replace("python.exe", "node.exe") if "node.exe" in sys.executable else "node", str(test_file)], capture_output=True, text=True)
    assert res.returncode == 0, f"Node tests failed:\n{res.stdout}\n{res.stderr}"
    assert "All 11 /api/enquiry unit tests passed cleanly!" in res.stdout

def test_api_enquiry_failure_path_browser_test():
    """Execute the failure path test verifying error alert, WhatsApp prefill, and form data preservation."""
    test_file = Path(__file__).parent.parent / "scratch" / "test_failure_path.js"
    res = subprocess.run([sys.executable.replace("python.exe", "node.exe") if "node.exe" in sys.executable else "node", str(test_file)], capture_output=True, text=True)
    assert res.returncode == 0, f"Failure path test failed:\n{res.stdout}\n{res.stderr}"
    assert "FAILURE-PATH TEST PASSED" in res.stdout
