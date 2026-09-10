#!/usr/bin/env python3
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Summarize inspected files for one zip archive")
    parser.add_argument("-z", "--zip-name", required=True, help="Name or label of zip archive")
    parser.add_argument("-i", "--infos", nargs="+", required=True, help="Paths to file info reports")
    parser.add_argument("-o", "--output", default="zip_summary.txt", help="Output summary file")
    args = parser.parse_args()

    lines = [f"=== Summary for {args.zip_name} (total files: {len(args.infos)}) ==="]
    for info_path in sorted(args.infos):
        with open(info_path, "r") as f:
            lines.append("  " + f.read().strip())

    with open(args.output, "w") as out:
        out.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
