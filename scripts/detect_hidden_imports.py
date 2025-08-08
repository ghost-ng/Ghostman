#!/usr/bin/env python3
"""
Hidden Imports Detection Script for PyInstaller
Analyzes Python code to detect potentially missing imports for PyInstaller builds
"""

import ast
import sys
import os
import importlib.util
from pathlib import Path
from collections import defaultdict
import argparse


class ImportAnalyzer:
    """Analyzes Python files to detect imports and potential hidden imports."""
    
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.all_imports = set()
        self.dynamic_imports = set()
        self.conditional_imports = set()
        self.third_party_imports = set()
        self.stdlib_imports = set()
        self.local_imports = set()
        self.import_sources = defaultdict(list)
        
    def is_stdlib_module(self, module_name):
        """Check if a module is part of the Python standard library."""
        stdlib_modules = {
            'os', 'sys', 'json', 're', 'time', 'datetime', 'pathlib', 'collections',
            'itertools', 'functools', 'typing', 'dataclasses', 'enum', 'abc',
            'asyncio', 'concurrent', 'threading', 'multiprocessing', 'queue',
            'urllib', 'http', 'xml', 'html', 'email', 'socket', 'ssl',
            'hashlib', 'hmac', 'secrets', 'uuid', 'random', 'math', 'statistics',
            'decimal', 'fractions', 'sqlite3', 'csv', 'configparser', 'logging',
            'argparse', 'shutil', 'tempfile', 'glob', 'fnmatch', 'linecache',
            'pickle', 'copyreg', 'copy', 'pprint', 'repr', 'numbers', 'cmath',
            'operator', 'contextlib', 'traceback', 'warnings', 'inspect',
            'importlib', 'pkgutil', 'modulefinder', 'runpy', 'parser', 'dis',
            'pickletools', 'platform', 'ctypes', 'struct', 'codecs', 'unicodedata',
            'stringprep', 'readline', 'rlcompleter', 'zipfile', 'tarfile',
            'gzip', 'bz2', 'lzma', 'zlib', 'base64', 'binhex', 'binascii',
            'quopri', 'uu', 'mimetypes', 'encodings'
        }
        
        return module_name.split('.')[0] in stdlib_modules
        
    def is_local_module(self, module_name, file_path):
        """Check if a module is local to the project."""
        # Check if it's a relative import or starts with project structure
        if module_name.startswith('.'):
            return True
            
        # Check if module exists in project directory
        project_modules = []
        for py_file in self.project_path.rglob('*.py'):
            rel_path = py_file.relative_to(self.project_path)
            module_path = str(rel_path.with_suffix('')).replace(os.sep, '.')
            project_modules.append(module_path)
            
        return module_name in project_modules
        
    def analyze_file(self, file_path):
        """Analyze a single Python file for imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            file_imports = self._extract_imports(tree, file_path)
            
            return file_imports
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return set()
            
    def _extract_imports(self, tree, file_path):
        """Extract imports from AST."""
        file_imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    self._categorize_import(module_name, file_path, 'direct')
                    file_imports.add(module_name)
                    
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    self._categorize_import(module_name, file_path, 'from')
                    file_imports.add(module_name)
                    
                    # Also add sub-imports
                    for alias in node.names:
                        if alias.name != '*':
                            full_name = f"{module_name}.{alias.name}"
                            self._categorize_import(full_name, file_path, 'from_sub')
                            file_imports.add(full_name)
                            
            # Detect dynamic imports
            elif isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Name) and 
                    node.func.id in ['__import__', 'importlib.import_module']):
                    if node.args and isinstance(node.args[0], ast.Constant):
                        module_name = node.args[0].value
                        self.dynamic_imports.add(module_name)
                        self._categorize_import(module_name, file_path, 'dynamic')
                        file_imports.add(module_name)
                        
        return file_imports
        
    def _categorize_import(self, module_name, file_path, import_type):
        """Categorize import and track its source."""
        self.all_imports.add(module_name)
        self.import_sources[module_name].append({
            'file': str(file_path),
            'type': import_type
        })
        
        if self.is_stdlib_module(module_name):
            self.stdlib_imports.add(module_name)
        elif self.is_local_module(module_name, file_path):
            self.local_imports.add(module_name)
        else:
            self.third_party_imports.add(module_name)
            
    def analyze_project(self):
        """Analyze the entire project for imports."""
        python_files = list(self.project_path.rglob('*.py'))
        
        print(f"Analyzing {len(python_files)} Python files...")
        
        for py_file in python_files:
            if 'test' not in str(py_file).lower():  # Skip test files
                self.analyze_file(py_file)
                
    def get_potential_hidden_imports(self):
        """Get list of potential hidden imports for PyInstaller."""
        # Focus on third-party imports and known problematic modules
        hidden_imports = set()
        
        # Add all third-party imports
        hidden_imports.update(self.third_party_imports)
        
        # Add dynamic imports
        hidden_imports.update(self.dynamic_imports)
        
        # Add known PyQt6 hidden imports
        pyqt6_modules = {
            'PyQt6.sip', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
            'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets'
        }
        
        # Add known OpenAI/requests hidden imports
        ai_modules = {
            'openai._client', 'openai._streaming', 'openai._base_client',
            'openai._exceptions', 'openai.types', 'openai.types.chat',
            'requests.packages.urllib3', 'requests.adapters', 'urllib3.poolmanager',
            'certifi', 'charset_normalizer', 'idna'
        }
        
        # Add known Pydantic hidden imports
        pydantic_modules = {
            'pydantic.dataclasses', 'pydantic.json', 'pydantic.types',
            'pydantic._internal', 'typing_extensions', 'annotated_types'
        }
        
        # Check if these modules are relevant
        for module_set in [pyqt6_modules, ai_modules, pydantic_modules]:
            for module in module_set:
                base_module = module.split('.')[0]
                if any(imp.startswith(base_module) for imp in self.third_party_imports):
                    hidden_imports.add(module)
                    
        return sorted(hidden_imports)
        
    def generate_spec_file_snippet(self):
        """Generate spec file snippet with hidden imports."""
        hidden_imports = self.get_potential_hidden_imports()
        
        snippet = "# Hidden imports detected by import analyzer\nhiddenimports = [\n"
        for imp in hidden_imports:
            snippet += f"    '{imp}',\n"
        snippet += "]\n"
        
        return snippet
        
    def generate_report(self):
        """Generate comprehensive import analysis report."""
        report = {
            'summary': {
                'total_imports': len(self.all_imports),
                'third_party_imports': len(self.third_party_imports),
                'stdlib_imports': len(self.stdlib_imports),
                'local_imports': len(self.local_imports),
                'dynamic_imports': len(self.dynamic_imports)
            },
            'third_party_modules': sorted(self.third_party_imports),
            'potential_hidden_imports': self.get_potential_hidden_imports(),
            'dynamic_imports': sorted(self.dynamic_imports),
            'import_sources': dict(self.import_sources)
        }
        
        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze Python project for hidden imports")
    parser.add_argument("project_path", nargs='?', default=".", 
                       help="Path to project root (default: current directory)")
    parser.add_argument("--output", "-o", help="Output file for report (JSON format)")
    parser.add_argument("--spec-snippet", action="store_true",
                       help="Generate spec file snippet")
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)
        
    print(f"Analyzing project: {project_path}")
    
    analyzer = ImportAnalyzer(project_path)
    analyzer.analyze_project()
    
    report = analyzer.generate_report()
    
    # Display summary
    print("\n" + "="*60)
    print("IMPORT ANALYSIS SUMMARY")
    print("="*60)
    print(f"Total imports found: {report['summary']['total_imports']}")
    print(f"Third-party imports: {report['summary']['third_party_imports']}")
    print(f"Standard library imports: {report['summary']['stdlib_imports']}")
    print(f"Local imports: {report['summary']['local_imports']}")
    print(f"Dynamic imports: {report['summary']['dynamic_imports']}")
    
    print(f"\nPotential hidden imports for PyInstaller ({len(report['potential_hidden_imports'])}):")
    for imp in report['potential_hidden_imports']:
        print(f"  - {imp}")
    
    # Generate spec file snippet
    if args.spec_snippet:
        print("\n" + "="*60)
        print("SPEC FILE SNIPPET")
        print("="*60)
        print(analyzer.generate_spec_file_snippet())
    
    # Save report if requested
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {args.output}")
    
    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()