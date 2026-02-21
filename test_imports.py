"""
Universal Import Error Detection Test
Checks all Python files in the project for import errors, module errors, 
and relative import issues.
"""

import sys
import os
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


class ImportTestSuite:
    """Test suite to validate all imports in the project."""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.results = {
            "passed": [],
            "failed": [],
            "skipped": [],
            "warnings": []
        }
        self.python_files = []
    
    def find_all_python_files(self) -> List[str]:
        """Find all Python files in the project (excluding __pycache__ and venv)."""
        exclude_dirs = {"__pycache__", ".git", ".pytest_cache", "venv", "env"}
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith(".py") and not file.startswith("."):
                    filepath = os.path.join(root, file)
                    python_files.append(filepath)
        
        self.python_files = sorted(python_files)
        return python_files
    
    def get_module_name(self, filepath: str) -> str:
        """Convert file path to module name."""
        rel_path = os.path.relpath(filepath, self.project_root)
        module_name = rel_path.replace(os.sep, ".").replace(".py", "")
        return module_name
    
    def test_direct_file_import(self, filepath: str) -> Tuple[bool, str]:
        """Test importing a file directly using importlib."""
        try:
            spec = importlib.util.spec_from_file_location(
                os.path.basename(filepath).replace(".py", ""), 
                filepath
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                return True, "✅ Direct import successful"
            else:
                return False, "❌ Could not create module spec"
        except ImportError as e:
            return False, f"❌ ImportError: {str(e)}"
        except ModuleNotFoundError as e:
            return False, f"❌ ModuleNotFoundError: {str(e)}"
        except Exception as e:
            return False, f"❌ Error: {type(e).__name__}: {str(e)}"
    
    def test_module_import(self, module_name: str) -> Tuple[bool, str]:
        """Test importing a module by name."""
        try:
            importlib.import_module(module_name)
            return True, "✅ Module import successful"
        except ImportError as e:
            return False, f"❌ ImportError: {str(e)}"
        except ModuleNotFoundError as e:
            return False, f"❌ ModuleNotFoundError: {str(e)}"
        except Exception as e:
            return False, f"❌ Error: {type(e).__name__}: {str(e)}"
    
    def check_for_relative_imports(self, filepath: str) -> List[str]:
        """Check file for problematic relative imports."""
        warnings = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    # Check for relative imports without package context
                    if stripped.startswith("from .") or stripped.startswith("import ."):
                        warnings.append(
                            f"  Line {i}: Relative import found: '{stripped}' "
                            "(May fail if run directly)"
                        )
        except Exception as e:
            warnings.append(f"  Could not read file: {str(e)}")
        
        return warnings
    
    def run_all_tests(self) -> Dict:
        """Run all import tests."""
        print("=" * 80)
        print("UNIVERSAL IMPORT ERROR DETECTION TEST")
        print("=" * 80)
        print(f"\nProject Root: {self.project_root}")
        print(f"Python Version: {sys.version}")
        print(f"Python Path: {sys.executable}\n")
        
        # Find all Python files
        python_files = self.find_all_python_files()
        print(f"Found {len(python_files)} Python files to test:\n")
        
        # Test each file
        for filepath in python_files:
            module_name = self.get_module_name(filepath)
            rel_path = os.path.relpath(filepath, self.project_root)
            
            print(f"\n{'-' * 80}")
            print(f"Testing: {rel_path}")
            print(f"Module: {module_name}")
            print(f"{'-' * 80}")
            
            # Skip __init__.py and test files in special cases
            if filepath.endswith("__init__.py"):
                print("⊘ Skipped (__init__.py)")
                self.results["skipped"].append(rel_path)
                continue
            
            # Check for relative imports
            relative_import_warnings = self.check_for_relative_imports(filepath)
            if relative_import_warnings:
                print("\n⚠️  Relative imports detected:")
                for warning in relative_import_warnings:
                    print(warning)
                    self.results["warnings"].append(f"{rel_path}: {warning}")
            
            # Test direct file import
            print("\n1. Direct File Import Test:")
            success, message = self.test_direct_file_import(filepath)
            print(f"   {message}")
            
            # Test module import (if applicable)
            print("\n2. Module Import Test:")
            if module_name != "__init__":
                success_module, message_module = self.test_module_import(module_name)
                print(f"   {message_module}")
            else:
                print("   ⊘ Module import skipped for __init__.py")
            
            # Record result
            if success:
                self.results["passed"].append(rel_path)
            else:
                self.results["failed"].append((rel_path, message))
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Print test results summary."""
        print("\n\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        print(f"\n✅ PASSED: {len(self.results['passed'])} files")
        if self.results['passed']:
            for file in self.results['passed']:
                print(f"   • {file}")
        
        print(f"\n❌ FAILED: {len(self.results['failed'])} files")
        if self.results['failed']:
            for file, error in self.results['failed']:
                print(f"   • {file}")
                print(f"     {error}")
        
        print(f"\n⊘ SKIPPED: {len(self.results['skipped'])} files")
        if self.results['skipped']:
            for file in self.results['skipped']:
                print(f"   • {file}")
        
        print(f"\n⚠️  WARNINGS: {len(self.results['warnings'])} issues")
        if self.results['warnings']:
            for warning in self.results['warnings']:
                print(f"   • {warning}")
        
        # Final verdict
        print("\n" + "-" * 80)
        if not self.results['failed']:
            print("✅ ALL TESTS PASSED - No Import Errors Detected!")
        else:
            print(f"❌ {len(self.results['failed'])} IMPORT ERROR(S) FOUND - See details above")
        
        print("=" * 80 + "\n")


def main():
    """Main entry point."""
    tester = ImportTestSuite(PROJECT_ROOT)
    results = tester.run_all_tests()
    
    # Exit with error code if failures found
    return 0 if not results['failed'] else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
