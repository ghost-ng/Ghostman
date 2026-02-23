#!/usr/bin/env python3
"""
Release Management Script for specter
Automates the release process including version bumping, tagging, and pushing
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_script(script_path, args):
    """Run a Python script with arguments"""
    cmd = [sys.executable, script_path] + args
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Script failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Release specter")
    parser.add_argument('version_type', choices=['major', 'minor', 'patch'],
                       help='Type of version bump')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path("specter").exists():
        print("❌ Error: Run this script from the specter root directory")
        sys.exit(1)
    
    scripts_dir = Path("scripts")
    version_script = scripts_dir / "version_bump.py"
    
    if not version_script.exists():
        print(f"❌ Error: Version bump script not found at {version_script}")
        sys.exit(1)
    
    # Show what will be done
    print(f"🚀 Release Process for specter")
    print(f"📋 Version bump type: {args.version_type}")
    print(f"🔧 Steps:")
    print(f"   1. Bump version ({args.version_type})")
    print(f"   2. Commit version change")
    print(f"   3. Create and push git tag")
    print(f"   4. GitHub Actions will automatically:")
    print(f"      - Build executables for Windows, Linux, macOS")
    print(f"      - Build Python packages")
    print(f"      - Create GitHub release with artifacts")
    
    if args.dry_run:
        print(f"\\n🔍 Dry run mode - no changes will be made")
        return
    
    # Confirm
    print(f"\\n⚠️  This will create a new release and trigger automated builds.")
    response = input(f"Continue with {args.version_type} release? [y/N]: ")
    if response.lower() not in ['y', 'yes']:
        print("❌ Release cancelled")
        sys.exit(0)
    
    # Run version bump with tag and push
    version_args = [args.version_type, '--tag', '--push']
    
    print(f"\\n🔄 Running version bump...")
    if not run_script(str(version_script), version_args):
        print(f"❌ Release failed during version bump")
        sys.exit(1)
    
    print(f"\\n🎉 Release process initiated successfully!")
    print(f"📡 GitHub Actions should now be building the release.")
    print(f"🔗 Check progress at: https://github.com/specter/specter/actions")

if __name__ == "__main__":
    main()