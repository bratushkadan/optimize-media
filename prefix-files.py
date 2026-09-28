#!/usr/bin/env python3
"""
Prefix all files in the current directory with a given prefix.
Usage: python prefix_files.py <prefix>
"""

import os
import sys
import argparse
from pathlib import Path


def prefix_files(prefix, directory=".", dry_run=False, verbose=False):
    """
    Prefix all files in the given directory with the specified prefix.
    
    Args:
        prefix: String to prepend to filenames
        directory: Directory to process (default: current directory)
        dry_run: If True, only show what would be done without renaming
        verbose: If True, print each rename operation
    
    Returns:
        Tuple of (success_count, skipped_count, error_count)
    """
    success = 0
    skipped = 0
    errors = 0
    
    directory_path = Path(directory)
    
    if not directory_path.is_dir():
        print(f"Error: '{directory}' is not a valid directory", file=sys.stderr)
        return 0, 0, 1
    
    # Get all files (not directories) in the directory
    for item in directory_path.iterdir():
        # Skip directories
        if item.is_dir():
            continue
        
        # Skip if already prefixed (optional - comment out if not desired)
        if item.name.startswith(prefix):
            if verbose:
                print(f"Skipping (already prefixed): {item.name}")
            skipped += 1
            continue
        
        new_name = f"{prefix}{item.name}"
        new_path = item.parent / new_name
        
        # Check if target already exists
        if new_path.exists():
            print(f"Error: '{new_name}' already exists, skipping '{item.name}'", 
                  file=sys.stderr)
            errors += 1
            continue
        
        try:
            if dry_run:
                print(f"[DRY RUN] Would rename: {item.name} -> {new_name}")
            else:
                item.rename(new_path)
                if verbose:
                    print(f"Renamed: {item.name} -> {new_name}")
            success += 1
        except OSError as e:
            print(f"Error renaming '{item.name}': {e}", file=sys.stderr)
            errors += 1
    
    return success, skipped, errors


def main():
    parser = argparse.ArgumentParser(
        description="Prefix all files in a directory with a given prefix."
    )
    parser.add_argument(
        "prefix",
        help="The prefix to add to each filename"
    )
    parser.add_argument(
        "-d", "--directory",
        default=".",
        help="Directory to process (default: current directory)"
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Show what would be done without actually renaming files"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print each rename operation"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Allow prefix that could cause issues (e.g., containing path separators)"
    )
    
    args = parser.parse_args()
    
    # Validate prefix
    if not args.prefix:
        print("Error: Prefix cannot be empty", file=sys.stderr)
        sys.exit(1)
    
    if not args.force:
        if os.sep in args.prefix or (os.altsep and os.altsep in args.prefix):
            print(f"Error: Prefix contains path separator. Use --force to override.",
                  file=sys.stderr)
            sys.exit(1)
        if args.prefix in (".", ".."):
            print(f"Error: Invalid prefix '{args.prefix}'", file=sys.stderr)
            sys.exit(1)
    
    success, skipped, errors = prefix_files(
        args.prefix,
        directory=args.directory,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    # Print summary
    print(f"\nSummary: {success} renamed, {skipped} skipped, {errors} errors")
    
    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()