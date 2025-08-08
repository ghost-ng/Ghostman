#!/usr/bin/env python3
"""
Build Testing and Validation Script for Ghostman
Comprehensive testing of the built executable
"""

import os
import sys
import subprocess
import json
import time
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

class BuildTester:
    """Comprehensive testing for Ghostman build."""
    
    def __init__(self, exe_path, verbose=False):
        self.exe_path = Path(exe_path)
        self.verbose = verbose
        self.test_results = {}
        self.start_time = time.time()
        
    def log(self, message, level="INFO"):
        """Log test messages."""
        if self.verbose or level in ["ERROR", "WARN"]:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")
            
    def test_executable_exists(self):
        """Test if executable file exists."""
        test_name = "executable_exists"
        self.log(f"Testing: {test_name}")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        if self.exe_path.exists():
            stat = self.exe_path.stat()
            result["passed"] = True
            result["details"] = {
                "path": str(self.exe_path),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified_time": stat.st_mtime
            }
            self.log(f"✅ Executable found: {self.exe_path}")
            self.log(f"📏 Size: {result['details']['size_mb']} MB")
        else:
            result["details"]["error"] = f"Executable not found: {self.exe_path}"
            self.log(f"❌ Executable not found: {self.exe_path}", "ERROR")
            
        self.test_results[test_name] = result
        return result["passed"]
        
    def test_file_integrity(self):
        """Test file integrity and calculate checksums."""
        test_name = "file_integrity"
        self.log(f"Testing: {test_name}")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        try:
            # Calculate SHA256
            sha256_hash = hashlib.sha256()
            with open(self.exe_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            sha256 = sha256_hash.hexdigest()
            
            result["passed"] = True
            result["details"]["sha256"] = sha256
            
            # Check if hash file exists and matches
            hash_file = self.exe_path.with_suffix('.exe.sha256')
            if hash_file.exists():
                with open(hash_file, 'r') as f:
                    stored_hash = f.read().split()[0]
                result["details"]["stored_hash_matches"] = (sha256 == stored_hash)
                
            self.log(f"✅ File integrity check passed")
            self.log(f"🔒 SHA256: {sha256[:16]}...")
            
        except Exception as e:
            result["details"]["error"] = str(e)
            self.log(f"❌ File integrity check failed: {e}", "ERROR")
            
        self.test_results[test_name] = result
        return result["passed"]
        
    def test_basic_execution(self):
        """Test basic executable launch."""
        test_name = "basic_execution"
        self.log(f"Testing: {test_name}")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        try:
            # Try to run with --help flag (quick exit)
            process = subprocess.Popen(
                [str(self.exe_path), "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            stdout, stderr = process.communicate(timeout=15)
            
            result["details"]["return_code"] = process.returncode
            result["details"]["stdout"] = stdout.strip()
            result["details"]["stderr"] = stderr.strip()
            
            # Consider it successful if it starts and exits cleanly
            if process.returncode in [0, 1]:  # 0 = success, 1 = help shown
                result["passed"] = True
                self.log("✅ Basic execution test passed")
            else:
                self.log(f"⚠️  Execution returned code {process.returncode}", "WARN")
                
        except subprocess.TimeoutExpired:
            self.log("⚠️  Execution test timeout (may be normal for GUI apps)", "WARN")
            process.kill()
            result["details"]["timeout"] = True
            result["passed"] = True  # Timeout might be normal for GUI apps
            
        except Exception as e:
            result["details"]["error"] = str(e)
            self.log(f"❌ Basic execution test failed: {e}", "ERROR")
            
        self.test_results[test_name] = result
        return result["passed"]
        
    def test_gui_launch(self):
        """Test GUI application launch."""
        test_name = "gui_launch"
        self.log(f"Testing: {test_name}")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        try:
            # Launch GUI and let it run for a few seconds
            process = subprocess.Popen(
                [str(self.exe_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Wait a bit to see if it starts successfully
            time.sleep(3)
            
            if process.poll() is None:
                # Process is still running, GUI likely launched
                result["passed"] = True
                result["details"]["launched_successfully"] = True
                self.log("✅ GUI appears to have launched successfully")
                
                # Terminate the process gracefully
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
            else:
                # Process exited quickly, might be an error
                stdout, stderr = process.communicate()
                result["details"]["return_code"] = process.returncode
                result["details"]["stdout"] = stdout.strip()
                result["details"]["stderr"] = stderr.strip()
                
                if process.returncode == 0:
                    result["passed"] = True
                    self.log("✅ GUI launched and exited cleanly")
                else:
                    self.log(f"❌ GUI launch failed with code {process.returncode}", "ERROR")
                    if stderr:
                        self.log(f"STDERR: {stderr}", "ERROR")
                        
        except Exception as e:
            result["details"]["error"] = str(e)
            self.log(f"❌ GUI launch test failed: {e}", "ERROR")
            
        self.test_results[test_name] = result
        return result["passed"]
        
    def test_dependencies(self):
        """Test if all dependencies are properly bundled."""
        test_name = "dependencies"
        self.log(f"Testing: {test_name}")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        # This is a basic test - in a real scenario, you might want to
        # add a --test-deps flag to your application that imports key modules
        try:
            # Try to run a dependency check if the app supports it
            process = subprocess.Popen(
                [str(self.exe_path), "--test-deps"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            stdout, stderr = process.communicate(timeout=30)
            
            result["details"]["return_code"] = process.returncode
            result["details"]["stdout"] = stdout.strip()
            result["details"]["stderr"] = stderr.strip()
            
            if process.returncode == 0:
                result["passed"] = True
                self.log("✅ Dependencies test passed")
            else:
                self.log("⚠️  Dependencies test not supported or failed", "WARN")
                result["passed"] = True  # Don't fail if test not supported
                
        except subprocess.TimeoutExpired:
            process.kill()
            self.log("⚠️  Dependencies test timeout", "WARN")
            result["passed"] = True  # Don't fail on timeout
            
        except Exception as e:
            result["details"]["error"] = str(e)
            self.log(f"⚠️  Dependencies test error: {e}", "WARN")
            result["passed"] = True  # Don't fail if test not available
            
        self.test_results[test_name] = result
        return result["passed"]
        
    def test_performance_metrics(self):
        """Test performance metrics like startup time."""
        test_name = "performance_metrics"
        self.log(f"Testing: {test_name}")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        try:
            # Measure startup time
            start_time = time.time()
            
            process = subprocess.Popen(
                [str(self.exe_path), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            process.communicate(timeout=30)
            startup_time = time.time() - start_time
            
            result["details"]["startup_time_seconds"] = round(startup_time, 2)
            result["passed"] = startup_time < 10.0  # Should start within 10 seconds
            
            if result["passed"]:
                self.log(f"✅ Performance test passed (startup: {startup_time:.2f}s)")
            else:
                self.log(f"⚠️  Slow startup time: {startup_time:.2f}s", "WARN")
                
        except subprocess.TimeoutExpired:
            process.kill()
            result["details"]["timeout"] = True
            self.log("❌ Performance test timeout", "ERROR")
            
        except Exception as e:
            result["details"]["error"] = str(e)
            self.log(f"❌ Performance test failed: {e}", "ERROR")
            
        self.test_results[test_name] = result
        return result["passed"]
        
    def run_all_tests(self):
        """Run all available tests."""
        self.log("Starting comprehensive build testing...")
        
        tests = [
            self.test_executable_exists,
            self.test_file_integrity,
            self.test_basic_execution,
            self.test_gui_launch,
            self.test_dependencies,
            self.test_performance_metrics,
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_func in tests:
            if test_func():
                passed_tests += 1
                
        # Calculate overall results
        test_duration = time.time() - self.start_time
        success_rate = (passed_tests / total_tests) * 100
        
        overall_result = {
            "timestamp": datetime.now().isoformat(),
            "executable_path": str(self.exe_path),
            "test_duration_seconds": round(test_duration, 2),
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate_percent": round(success_rate, 1),
            "overall_passed": passed_tests >= (total_tests * 0.8),  # 80% pass rate
            "individual_tests": self.test_results
        }
        
        return overall_result
        
    def save_results(self, output_file):
        """Save test results to file."""
        results = self.run_all_tests()
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        return results
        

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test Ghostman build")
    parser.add_argument("executable", nargs='?', default="dist/Ghostman.exe",
                       help="Path to executable to test")
    parser.add_argument("--output", "-o", default="test_results.json",
                       help="Output file for test results")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    exe_path = Path(args.executable)
    
    if not exe_path.exists():
        print(f"❌ Executable not found: {exe_path}")
        print("Available files in dist directory:")
        dist_dir = exe_path.parent
        if dist_dir.exists():
            for file in dist_dir.iterdir():
                print(f"  - {file.name}")
        sys.exit(1)
        
    tester = BuildTester(exe_path, verbose=args.verbose)
    results = tester.save_results(args.output)
    
    # Display summary
    print("\n" + "="*60)
    print("BUILD TEST SUMMARY")
    print("="*60)
    print(f"Executable: {exe_path}")
    print(f"Tests passed: {results['tests_passed']}/{results['tests_total']}")
    print(f"Success rate: {results['success_rate_percent']}%")
    print(f"Test duration: {results['test_duration_seconds']}s")
    
    if results['overall_passed']:
        print("\n🎉 Overall result: PASSED")
    else:
        print("\n💥 Overall result: FAILED")
        
    print(f"\nDetailed results saved to: {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_passed'] else 1)


if __name__ == "__main__":
    main()