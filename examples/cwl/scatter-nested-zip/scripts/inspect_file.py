#!/usr/bin/env python3
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Inspect file size and content snippet")
    parser.add_argument("-f", "--file", required=True, help="Path to input file")
    parser.add_argument("-o", "--output", default="file_info.txt", help="Output summary file")
    args = parser.parse_args()

    fname = os.path.basename(args.file)
    size = os.path.getsize(args.file)
    try:
        with open(args.file, "r", errors="replace") as f:
            snippet = f.read(50).strip().replace("\n", " ")
    except Exception as e:
        snippet = f"<binary or unreadable: {e}>"

    with open(args.output, "w") as out:
        out.write(f"file: {fname} | size: {size} bytes | preview: '{snippet}'\n")

if __name__ == "__main__":
    main()
