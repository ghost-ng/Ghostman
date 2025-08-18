#!/usr/bin/env python3
"""
Version Bump Script for ghost-ng
Manages semantic versioning and git tagging
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

def get_current_version():
    """Get the current version from __version__.py"""
    version_file = Path("ghostman") / "__version__.py"
    if not version_file.exists():
        raise FileNotFoundError("Version file not found")
    
    content = version_file.read_text()
    version_match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if not version_match:
        raise ValueError("Version not found in version file")
    
    return version_match.group(1)

def parse_version(version_str):
    """Parse version string into components"""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-([^+]+))?(?:\+(.+))?$', version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    
    major, minor, patch, pre_release, build = match.groups()
    return {
        'major': int(major),
        'minor': int(minor),
        'patch': int(patch),
        'pre_release': pre_release,
        'build': build
    }

def bump_version(current_version, bump_type):
    """Bump version according to type"""
    version_parts = parse_version(current_version)
    
    if bump_type == 'major':
        version_parts['major'] += 1
        version_parts['minor'] = 0
        version_parts['patch'] = 0
    elif bump_type == 'minor':
        version_parts['minor'] += 1
        version_parts['patch'] = 0
    elif bump_type == 'patch':
        version_parts['patch'] += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")
    
    # Clear pre-release and build for regular bumps
    version_parts['pre_release'] = None
    version_parts['build'] = None
    
    new_version = f"{version_parts['major']}.{version_parts['minor']}.{version_parts['patch']}"
    return new_version

def update_version_file(new_version):
    """Update the version in __version__.py"""
    version_file = Path("ghostman") / "__version__.py"
    content = version_file.read_text()
    
    # Update __version__
    content = re.sub(
        r'__version__ = ["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    
    # Update VERSION_* constants
    version_parts = parse_version(new_version)
    content = re.sub(
        r'VERSION_MAJOR = \d+',
        f'VERSION_MAJOR = {version_parts["major"]}',
        content
    )
    content = re.sub(
        r'VERSION_MINOR = \d+',
        f'VERSION_MINOR = {version_parts["minor"]}',
        content
    )
    content = re.sub(
        r'VERSION_PATCH = \d+',
        f'VERSION_PATCH = {version_parts["patch"]}',
        content
    )
    content = re.sub(
        r'VERSION_INFO = \([^)]+\)',
        f'VERSION_INFO = ({version_parts["major"]}, {version_parts["minor"]}, {version_parts["patch"]})',
        content
    )
    
    version_file.write_text(content)
    print(f"✅ Updated version file to {new_version}")

def run_command(cmd, description):
    """Run a shell command"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"   Error: {e.stderr.strip()}")
        return False

def create_git_tag(version, push=False):
    """Create and optionally push git tag"""
    tag_name = f"v{version}"
    
    # Create tag
    if not run_command(f'git tag -a {tag_name} -m "Release {tag_name}"', f"Creating tag {tag_name}"):
        return False
    
    # Push tag if requested
    if push:
        if not run_command(f'git push origin {tag_name}', f"Pushing tag {tag_name}"):
            return False
    
    return True

def check_git_status():
    """Check if git working directory is clean"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print("❌ Git working directory is not clean. Please commit or stash changes first.")
            print("Uncommitted changes:")
            print(result.stdout)
            return False
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to check git status")
        return False

def main():
    parser = argparse.ArgumentParser(description="Bump version for ghost-ng")
    parser.add_argument('bump_type', choices=['major', 'minor', 'patch'],
                       help='Type of version bump')
    parser.add_argument('--tag', action='store_true',
                       help='Create git tag for the new version')
    parser.add_argument('--push', action='store_true',
                       help='Push the tag to origin (requires --tag)')
    parser.add_argument('--force', action='store_true',
                       help='Skip git status check')
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path("ghostman").exists():
        print("❌ Error: Run this script from the ghost-ng root directory")
        sys.exit(1)
    
    # Check git status unless forced
    if not args.force and not check_git_status():
        sys.exit(1)
    
    try:
        # Get current version
        current_version = get_current_version()
        print(f"📋 Current version: {current_version}")
        
        # Calculate new version
        new_version = bump_version(current_version, args.bump_type)
        print(f"🚀 New version: {new_version}")
        
        # Confirm the bump
        response = input(f"Proceed with version bump to {new_version}? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Version bump cancelled")
            sys.exit(0)
        
        # Update version file
        update_version_file(new_version)
        
        # Commit the version change
        if not run_command('git add ghostman/__version__.py', "Staging version file"):
            sys.exit(1)
        
        if not run_command(f'git commit -m "Bump version to {new_version}"', "Committing version bump"):
            sys.exit(1)
        
        # Create tag if requested
        if args.tag:
            if not create_git_tag(new_version, args.push):
                sys.exit(1)
            
            if args.push:
                print(f"🎉 Version {new_version} bumped, committed, tagged, and pushed!")
            else:
                print(f"🎉 Version {new_version} bumped, committed, and tagged!")
                print(f"💡 To push the tag, run: git push origin v{new_version}")
        else:
            print(f"🎉 Version {new_version} bumped and committed!")
            print(f"💡 To create a tag, run: git tag -a v{new_version} -m 'Release v{new_version}'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()