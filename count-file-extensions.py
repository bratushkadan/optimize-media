#!/usr/bin/env python3
"""
Count file extensions in a directory (recursively) and print them in descending order.
"""

import os
import sys
from collections import Counter


def count_extensions(root_dir):
    """Walk root_dir and return a Counter of file extensions."""
    counter = Counter()

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            # os.path.splitext handles names like "archive.tar.gz" -> ".gz"
            ext = os.path.splitext(filename)[1].lower()
            
            # if ext in [".mp3"] and not os.path.exists(f'{dirpath}/{filename.lower().rstrip(".mp3")}.opus'):
            #     print(f'{os.path.splitext(filename)[0]}.opus', filename)

            # Files with no extension get an empty string; label them clearly
            counter[ext if ext else "<no extension>"] += 1

    return counter


def main():
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    if not os.path.isdir(root_dir):
        print(f"Error: '{root_dir}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    counter = count_extensions(root_dir)

    if not counter:
        print("No files found.")
        return

    # Sort by count descending, then by extension name for stable output
    for ext, count in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
        print(f"{count:>8}  {ext}")


if __name__ == "__main__":
    main()
